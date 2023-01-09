### A quick, REALLY unnecessarily design-patterned job-search record keeper

This project is, again, partly design pattern practice and mostly just something I wrote to make my life easier.

- On first run, just type in `python main.py new`. If you mess up and do it while applications.csv still exists, don't worry, it'll deny the overwrite.

- On subsequent runs, just go `python main.py csv`.

- Other than that, there's quite a few quick-entry features:
  - You can disobey the menu, and if you enter more than one keystroke while in the main menu, the program assumes you wanted to make another application.
  - Application quantities default to one, so if you're only applying for one position, just type the company name.

- There's also a utility to flatten the CSV so that jobs with the same company get grouped and the max date is chosen as the aggregation. This makes the application count of the present day dishonest in case you applied to one of the affected companies today, though, so make sure you understand that. The command is `python main.py clean`.

- We now have SQLite functionality as well! Provided you already have the CSV file, you can call `python main.py tosql`. This coalesces the CSV file and seeds an SQLite database with it. To then use the database in SQL mode, simply call `python main.py sql`!

- There's also a functionality to take an SQLite database as an input and parse it to a csv format. Just call `python main.py tocsv` and it'll do it for you! Might be handy to correct small mistakes to do something like `python main.py tocsv` -> Change the csv manually -> Delete the SQLite file -> `python main.py tosql`.