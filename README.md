# flockx timecard
## Purpose
Python script to generate timecard from three input files:
* approved_hours.csv (shows approved hours a daily detail)
* summary_hours.csv (shows total hours by category)
* payroll_info.csv (Employee #,Hire Date,Name,Job Title,Location,Work Schedule,Employment Status,Manager)

## Generating Executable file


## Limitations
In order for the python executable to find files on local computer, the directory needed to be hardcoded
* Script expects the root to be in this folder: `users/<username>/timecard`
* Date labels in report might be inaccurate if period crosses a calendar year

## Future Enhancements
Some kind of envar/setting to update the root directory

## Instructions for Install
### Enable Viewing Harddrive in finder (if needed)
If user can not already see their hard drive, this can be enabled as "showing hard drive" in finder settings, and then enable "hard drive in sidebar" in sidebar settings

### Permissions
To allow running an executable from unknown developer:
* Go to Settings -> Privacy and Security and then find file and allow  

### Make a file executable
* Open terminal
* Navigate to folder
* run `chmod +x ./timecard`


# Versions
0.1 Initial Release (May 2025)
0.2 Updated format to 2 decimal places (6/3/25)

