# Back-End For Habit Tracker By Garv Vikram Gursahaney

import sqlite3
from datetime import datetime, timedelta
import atexit

# Add SQlite database to connect to code. I used this as an example database
conn = sqlite3.connect('habit_tracker_backend.db')
cursor = conn.cursor()

# Creation of a user table
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL
                    )''')

# Creation of a habit table
cursor.execute('''CREATE TABLE IF NOT EXISTS habits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_description TEXT NOT NULL,
                        periodicity INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

# Creation of a completed habit table
cursor.execute('''CREATE TABLE IF NOT EXISTS completed_habits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        habit_id INTEGER NOT NULL,
                        completion_date TIMESTAMP NOT NULL,
                        FOREIGN KEY (habit_id) REFERENCES habits (id)
                    )''')

class Habit:
    def __init__(self, task_description, periodicity):
        '''
        Input a new Habit with an input for a task and how often it should be done.

        Arguments include:
            task_description (str): The description of the habit.
            periodicity (int): Number of days between each repetition of the task.
        '''
        self.task_description = task_description
        self.periodicity = periodicity

    def complete_task(self, user_id):
        '''
        Add the current date and time to the completed_habits table to ensure accuracy of time-sensitive tasks.

        Arguments include:
            user_id (int): The ID of the user who completed the habit.
        '''
        cursor.execute("INSERT INTO completed_habits (habit_id, completion_date) VALUES (?, ?)",
                       (self.get_habit_id(user_id), datetime.now()))
        conn.commit()

    def is_completed(self, user_id, date):
        '''
        Check if the habit is completed on the selected date.

        Arguments include:
            user_id (int): The ID of the user.
            date (str): Date to check for completion.

        Returns:
            boolean: True if the habit is completed on the date, otherwise False.
        '''
        cursor.execute("SELECT COUNT(*) FROM completed_habits WHERE habit_id=? AND completion_date=?",
                       (self.get_habit_id(user_id), date))
        return cursor.fetchone()[0] > 0

    def is_broken(self, user_id):
        '''
        Check if the habit is not completed or "broken" by the user.

        Arguments include:
            user_id (int): The ID of the user within the code.

        Returns:
            boolean: True if the habit is completed on the date, otherwise False.
        '''
        last_completed_date = self.get_last_completed_date(user_id)
        if not last_completed_date:
            return True  # If the habit has never been completed, it is incomplete or "broken".

        next_period_start = last_completed_date + timedelta(days=self.periodicity)
        return next_period_start < datetime.now()

    def get_last_completed_date(self, user_id):
        '''
        Get the last completed date for the habit.

        Arguments include:
            user_id (int): The ID of the user.

        Returns:
            datetime: The last completed date or None if no completion is recorded.
        '''
        cursor.execute("SELECT MAX(completion_date) FROM completed_habits WHERE habit_id=?",
                       (self.get_habit_id(user_id),))
        last_completed_date = cursor.fetchone()[0]
        return last_completed_date if last_completed_date else None

    def get_habit_id(self, user_id):
        '''
        Get the habit's ID from the habit tracker backend database or insert a new habit if not found.

        Arguments include:
            user_id (int): The ID of the user.

        Returns:
            int: The habit's ID.
        '''
        cursor.execute("SELECT id FROM habits WHERE task_description=? AND periodicity=? AND user_id=?",
                       (self.task_description, self.periodicity, user_id))
        habit = cursor.fetchone()
        if habit:
            return habit[0]
        else:
            cursor.execute("INSERT INTO habits (task_description, periodicity, user_id) VALUES (?, ?, ?)",
                           (self.task_description, self.periodicity, user_id))
            conn.commit()
            return cursor.lastrowid

    def get_longest_streak(self, user_id):
        '''
        Calculate the streak of continuous successful tasks done every day in a row.

        Arguments include:
            user_id (int): The ID of the user.

        Returns:
            int: The longest streak.
        '''
        cursor.execute("SELECT DATE completion_date FROM completed_habits WHERE habit_id=? ORDER BY completion_date ASC",
                       (self.get_habit_id(user_id),))
        completion_dates = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in cursor.fetchall()]

        longest_streak = 0
        current_streak = 0
        for i in range(len(completion_dates)):
            if i == 0 or completion_dates[i] - completion_dates[i - 1] == timedelta(days=self.periodicity):
                current_streak += 1
            else:
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
        longest_streak = max(longest_streak, current_streak)
        return longest_streak

class User:
    def __init__(self, name):
        '''
        Initialize a new user with a name.

        Arguments include:
            name (str): The name of the user.
        '''
        self.name = name

    def add_habit(self, task_description, periodicity):
        '''
        Add a new habit for the user and store it automatically in the database.

        Arguments include:
            task_description (str): The description of the habit.
            periodicity (int): Number of days between each repetition of the task created by the user.
        '''
        habit = Habit(task_description, periodicity)
        conn.commit()  # Commit the habit creation

    def get_user_id(self):
        '''
        Get the user's ID from the database or insert a new user if not found.

        Returns:
            int: The user's ID.
        '''
        cursor.execute("SELECT id FROM users WHERE name=?", (self.name,))
        user = cursor.fetchone()
        if user:
            return user[0]
        else:
            cursor.execute("INSERT INTO users (name) VALUES (?)", (self.name,))
            conn.commit()
            return cursor.lastrowid

    def get_current_habits(self):
        '''
        Get the list of habits currently being tracked by the user.

        Returns:
            list: List of current habit descriptions.
        '''
        cursor.execute("SELECT task_description FROM habits WHERE user_id=?", (self.get_user_id(),))
        current_habits = [row[0] for row in cursor.fetchall()]
        return current_habits

    def get_struggled_habits(self, start_date, end_date):
        '''
        Get the habits that the user struggled with within a specific date range to show room for improvement.

        Arguments include:
            start_date (str): Start date of the range.
            end_date (str): End date of the range.

        Returns:
            list: List of struggled habit descriptions.
        '''
        struggled_habits = []
        cursor.execute("SELECT DISTINCT habit_id FROM completed_habits WHERE completion_date BETWEEN ? AND ?",
                       (start_date, end_date))
        completed_habit_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT task_description FROM habits WHERE user_id=?", (self.get_user_id(),))
        all_habit_descriptions = [row[0] for row in cursor.fetchall()]
        struggled_habits = [habit for habit in all_habit_descriptions if habit not in completed_habit_ids]
        return struggled_habits

class HabitTracker:
    def __init__(self):
        pass

    def add_user(self, name):
        '''
        Add a new user to the habit tracker.

        Arguments include:
            name (str): The name of the user.
        '''
        user = User(name)
        conn.commit()  # Commit the user creation

    def complete_habit(self, username, task_description):
        '''
        Mark a habit as completed for a specific user.

        Arguments  include:
            username (str): The username of the user.
            task_description (str): The description of the habit.
        '''
        user = User(username)
        habit = Habit(task_description, 1)
        habit.complete_task(user.get_user_id())  # Pass the user's ID
        conn.commit()  # Commit the habit completion

    def get_longest_streak(self, username, task_description):
        '''
        Get the longest streak for a specific habit of a user.

        Arguments include:
            username (str): The username of the user.
            task_description (str): The description of the habit.

        Returns:
            int: The longest streak for the habit.
        '''
        user = User(username)
        habit = Habit(task_description, 1)
        longest_streak = habit.get_longest_streak(user.get_user_id())  # Pass the user's ID
        return longest_streak

    def get_current_habits(self, username):
        '''
        Get the list of habits currently being tracked by a specific user.

        Arguments include:
            username (str): The username of the user.

        Returns:
            list: List of current habit descriptions.
        '''
        user = User(username)
        current_habits = user.get_current_habits()
        return current_habits

    def get_struggled_habits(self, username, start_date, end_date):
        '''
        Get the habits that a user struggled with within a specific date range to show room for improvement.

        Arguments include:
            username (str): The username of the user.
            start_date (str): Start date of the range.
            end_date (str): End date of the range.

        Returns:
            list: List of struggled habit descriptions.
        '''
        user = User(username)
        struggled_habits = user.get_struggled_habits(start_date, end_date)
        return struggled_habits

# Close the database connection when the program exits
atexit.register(conn.close)

# Predefined Habits and Example Tracking Data
def create_predefined_habits():
    habit_tracker = HabitTracker()
    predefined_habits = [
        ("Go To The Gym", 7),
        ("Read A Book", 1),
        ("Organize The Bed", 7),
        ("Drink 3 Litres Of Water", 7),
        ("Clean The House", 2),
    ]

    # Create a demo user
    habit_tracker.add_user("DemoUser")

    for habit in predefined_habits:
        # Complete predefined habits for the demo user
        habit_tracker.complete_habit("DemoUser", habit[0])
        print(f"Predefined Habit Added: {habit[0]}")

if __name__ == '__main__':
    create_predefined_habits()
