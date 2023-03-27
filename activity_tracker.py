from __future__ import print_function

import datetime
import time
import json
import win32gui

import matplotlib.pyplot as plt
from dateutil import parser
import uiautomation as auto


ALPHA = 0.8
SECONDS_PER_HOUR = 3600
ACTIVITIES_FILE = "activities.json"
JSON_DUMP_PARAMS = {"indent": 4, "sort_keys": True}


class Activity:
    """A class representing an activity.

    Attributes:
        name (str): The name of the activity.
        time_entries (list of TimeEntry): A list of time entries for this activity.

    Methods:
        serialize(): Returns a serialized dictionary representation of the activity.
    """

    def __init__(self, name, time_entries):
        self.name = name
        self.time_entries = time_entries

    def serialize(self):
        return {
            "name": self.name,
            "time_entries": [time.serialize() for time in self.time_entries]
        }


class TimeEntry:
    """A class representing a time entry.

    Attributes:
        start_time (datetime.datetime): The start time of the time entry.
        end_time (datetime.datetime): The end time of the time entry.
        total_time (datetime.timedelta): The total time elapsed during the time entry.

    Methods:
        serialize(): Returns a serialized dictionary representation of the time entry.
    """

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self.total_time = end_time - start_time

    def _get_specific_times(self):
        days, seconds = self.total_time.days, self.total_time.seconds
        self.hours = days * 24 + seconds // SECONDS_PER_HOUR
        self.minutes = (seconds % SECONDS_PER_HOUR) // 60
        self.seconds = seconds % 60

    def serialize(self):
        self._get_specific_times()
        return {
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "days": self.total_time.days,
            "hours": self.hours,
            "minutes": self.minutes,
            "seconds": self.seconds
        }


class ActivityList:
    """A class representing a list of activities.

    Attributes:
        activities (list of Activity): A list of activities.

    Methods:
        initialize(filepath): Initializes the activity list from a JSON file.
        serialize(): Returns a serialized dictionary representation of the activity list.
        plot_activities(): Plots a graph of the durations of the activities over time.
    """

    def __init__(self):
        self.activities = []

    def initialize(self, filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                self.activities = [Activity(activity["name"],
                                   self._get_time_entries_from_json(activity))
                                   for activity in data["activities"]]

        except FileNotFoundError:
            print("No JSON file found.")
        except json.decoder.JSONDecodeError:
            print("Invalid JSON data in activities.json. Creating a new file...")
            with open(filepath, "w") as f:
                json.dump({"activities": []}, f, **JSON_DUMP_PARAMS)

    def _get_time_entries_from_json(self, data):
        return [TimeEntry(parser.parse(entry["start_time"]),
                parser.parse(entry["end_time"]))
                for entry in data["time_entries"]]

    def serialize(self):
        return {
            "activities": [activity.serialize() for activity in self.activities]
        }

    def plot_activities(self):
        num_activities = len(self.activities)
        fig, axs = plt.subplots(1, num_activities, figsize=(15, 5))
        for i, activity in enumerate(self.activities):
            all_durations = [entry.total_time.total_seconds() / SECONDS_PER_HOUR
                            for entry in activity.time_entries]
            axs[i].hist(all_durations, alpha=ALPHA)
            axs[i].set_title(activity.name)
            axs[i].set_xlabel('Duration (hours)')
            axs[i].set_ylabel('Frequency')
        plt.show()



def url_to_name(url):
    """Extracts the name of a website from its URL.

    Args:
        url (str): The URL of the website.

    Returns:
        str: The name of the website.
    """
    string_list = url.split("/")
    return string_list[2]


def get_active_window_name():
    """Returns the name of the currently active window.

    Returns:
        str: The name of the currently active window.
    """
    window = win32gui.GetForegroundWindow()
    active_window_name = win32gui.GetWindowText(window)
    return active_window_name


def get_chrome_url():
    """Returns the URL of the currently active tab in Google Chrome.

    Returns:
        str: The URL of the currently active tab in Google Chrome.
    """
    window = win32gui.GetForegroundWindow()
    chrome_control = auto.ControlFromHandle(window)
    edit = chrome_control.EditControl()
    return f"https://{edit.GetValuePattern().Value}"


ACTIVE_WINDOW_NAME = ""
ACTIVITY_NAME = ""
START_TIME = datetime.datetime.now()
ACTIVE_LIST = ActivityList()
FIRST_TIME = True

# Create an instance of ActivityList and initialize it with data from the JSON file
activity_list = ActivityList()
activity_list.initialize("activities.json")

try:
    try:
        while True:
            previous_site = ""
            new_window_name = get_active_window_name()

            if "Google Chrome" in new_window_name:
                new_window_name = url_to_name(get_chrome_url())

            if ACTIVE_WINDOW_NAME != new_window_name:
                print(ACTIVE_WINDOW_NAME)
                ACTIVITY_NAME = ACTIVE_WINDOW_NAME

                if not FIRST_TIME:
                    end_time = datetime.datetime.now()
                    time_entry = TimeEntry(START_TIME, end_time)
                    time_entry._get_specific_times()

                    exists = False
                    for activity in ACTIVE_LIST.activities:
                        if activity.name == ACTIVITY_NAME:
                            exists = True
                            activity.time_entries.append(time_entry)

                    if not exists:
                        activity = Activity(ACTIVITY_NAME, [time_entry])
                        ACTIVE_LIST.activities.append(activity)
                    with open(ACTIVITIES_FILE, "w") as json_file:
                        json.dump(ACTIVE_LIST.serialize(), json_file,
                                  **JSON_DUMP_PARAMS)
                FIRST_TIME = False
                ACTIVE_WINDOW_NAME = new_window_name

            time.sleep(1)
    finally:
        # Plot the activities at the end of the script, after the loop has finished
        activity_list.plot_activities()
except KeyboardInterrupt:
    with open(ACTIVITIES_FILE, "w") as json_file:
        json.dump(ACTIVE_LIST.serialize(), json_file, **JSON_DUMP_PARAMS)
