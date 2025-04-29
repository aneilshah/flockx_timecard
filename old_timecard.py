# old_timecard.py - Read flockX Timecards and create report
import pandas as pd
import datetime

# Read the CSV files
timecard_detail_data = pd.read_csv("input/approved_hours.csv")
payroll_info = pd.read_csv("input/payroll_info.csv")
summary_hours = pd.read_csv("input/summary_hours.csv")

def get_week(month, day, year):
    date_obj = datetime.date(year, month, day)
    return date_obj.isocalendar().week

def non_blank(text, test):
    if test > 0.001:
        return f"{text},"
    return ''

# View the first 5 rows
print("TIMECARD DATA LOADED")
print(timecard_detail_data.head())
print("PAYROLL INFO LOADED")
print(payroll_info.head())
print("UNBILLED HOURS LOADED")
print(summary_hours.head())

# Process Payroll Info
info = {}
for idx in payroll_info.index:
    data = payroll_info.iloc[idx].to_dict()
    id = data['Employee #']
    hire_date = data['Hire Date']
    name = data['Name']
    title = data['Job Title']
    location = data['Location']
    schedule = data['Work Schedule']
    status = data['Employment Status']
    manager = data['Manager']
    info[id] = {
        "hire_date": hire_date,
        "name": name,
        "title": title,
        "location": location,
        "schedule": schedule,
        "status": status,
        "manager": manager
    }

print(info)

# Process Timecard
timecard_detail = {}
start_week = 52
end_day = 0
start_day = 20301231
start_date = 'NONE'
end_date = 'NONE'
for idx in timecard_detail_data.index:
    data = timecard_detail_data.iloc[idx].to_dict()
    id = data['Employee Number']
    date_txt = data['Date']
    date,time = date_txt.split(" ")
    year, month, day = date.split('-')
    month = int(month)
    day = int(day)
    year = int(year)
    week = get_week(month, day, year)

    # Find Start and End Time Period Data
    datecode = 10000 * year + 100 * month + day
    if week < start_week:
        start_week = week

    if datecode < start_day:
        start_date = date
        start_day = datecode

    if datecode > end_day:
        end_date = date
        end_day = datecode

    hours = data['Reg Hours']
    ot = 0 if pd.isna(data['OT Hours']) else data['OT Hours']
    timecard_detail[idx] = {
        'id': id,
        'hours': hours,
        'date': date,
        'month': month,
        'day': day,
        'week': week,
        'year': year,
        'ot': ot
    }
print(timecard_detail)
print(f'Start Week: {start_week}')
print(f'Start Day: {start_date}')
print(f'End Day: {end_date}')

# Process Timecard Summary Data
timecard_summary = {}
total = {
    'hours': 0,
    'ot': 0,
    'holiday': 0,
    'bereavement': 0,
    'personal': 0,
    'sick': 0,
    'sick_ca': 0,
    'vol': 0,
    'vote': 0,
    'pto': 0,
    'all_hrs': 0
}
for idx in summary_hours.index:
    data = summary_hours.iloc[idx].to_dict()
    id = data['Employee Number']
    hours = 0 if pd.isna(data['Regular']) else data['Regular']
    ot = 0 if pd.isna(data['Overtime']) else data['Overtime']
    holiday = 0 if pd.isna(data['Holiday']) else data['Holiday']
    bereavement = 0 if pd.isna(data['Bereavement']) else data['Bereavement']
    personal = 0 if pd.isna(data['Personal Day']) else data['Personal Day']
    sick = 0 if pd.isna(data['Sick Leave']) else data['Sick Leave']
    sick_ca = 0 if pd.isna(data['Sick Leave (CA)']) else data['Sick Leave (CA)']
    vol = 0 if pd.isna(data['Volunteer']) else data['Volunteer']
    vote = 0 if pd.isna(data['Voting']) else data['Voting']
    total_pto = 0 if pd.isna(data['Total PTO']) else data['Total PTO']
    total_hrs = 0 if pd.isna(data['Total Hours']) else data['Total Hours']
    approved = data['Approved?']

    total['hours'] += hours
    total['ot'] += ot
    total['holiday'] += holiday
    total['bereavement'] += bereavement
    total['personal'] += personal
    total['sick'] += sick
    total['sick_ca'] += sick_ca
    total['vol'] += vol
    total['vote'] += vote
    total['pto'] += total_pto
    total['all_hrs'] += total_hrs

    timecard_summary[id] = {
        "hours": hours,
        "ot": ot,
        "holiday": holiday,
        "bereavement": bereavement,
        "personal": personal,
        "sick": sick,
        "sick_ca": sick_ca,
        "vol": vol,
        "vote": vote,
        "total_pto": total_pto,
        "total_hrs": total_hrs,
        "approved": approved
    }
print(timecard_summary)

# Create Report
header = ['Work Schedule', 'Emp Status', 'Location', 'Employee Name',
          'Manager', 'Regular', 'OT', 'Holiday']
if total['sick'] > 0.1:
    header.append('Sick')
if total['sick_ca'] > 0.1:
    header.append('Sick (CA)')
if total['bereavement'] > 0.1:
    header.append('Bereavement')
if total['vol'] > 0.1:
    header.append('Vol')
if total['vote'] > 0.1:
    header.append('Vote')
header += ['Total PTO', 'Total Hrs', 'Approved?']

# Create HTML Header
summary_table = "<table>\n"

# Create the table's column headers
summary_table += "  <tr>\n"
for item in header:
    summary_table += f"    <th>{item}</th>\n"
summary_table += "  </tr>\n"

report_text = f"{','.join(header)}\n"

for id in timecard_summary:
    if id in info:
        name = f'"{info[id]["name"]}"'
        manager = info[id]['manager']
        location = info[id]['location']
        status = info[id]['status']
        schedule = info[id]['schedule']

    else:
        name = '*MISSING*'
        manager = '*MISSING*'
        location = '*MISSING*'
        status = '*MISSING*'
        schedule = '*MISSING*'

    tc = timecard_summary[id]
    row = [schedule,status,location,name,manager,str(tc['hours']),
           str(tc['ot']),str(tc['holiday'])]
    if total['sick'] > 0.1:
        row.append(tc['sick'])
    if total['sick_ca'] > 0.1:
        row.append(str(tc['sick_ca']))
    if total['bereavement'] > 0.1:
        row.append(str(tc['bereavement']))
    if total['vol'] > 0.1:
        row.append(str(tc['vol']))
    if total['vote'] > 0.1:
        row.append(str(tc['vote']))
    row += [str(tc['total_pto']),str(tc['total_hrs']),tc['approved']]
    txt = f"{','.join(row)}\n"

    # Create CSV
    report_text += txt

    # Create the table's row data
    summary_table += "  <tr>\n"
    for column in row:
        summary_table += "    <td>{0}</td>\n".format(column.strip())
    summary_table += "  </tr>\n"
summary_table += "</table>\n"

# Create Detail Table
detail_table = "<h3>Under Construction</h3>\n<table>\n"
detail_table += "</table>\n"

# Create HTML
html_text = '''<!DOCTYPE html>
<html>
<head>
<style>
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
  padding-left: 10px; 
  padding-right: 10px; 
}
</style>
</head>
<body>
<font size="2" face="Arial" >
'''
html_text += f'<h1>Timecard Report</h1>\n'
html_text += f'<h3>Work Period: {start_date} - {end_date}</h3>'
html_text += summary_table
html_text += '<br><h1>Timecard Details</h1>\n'
html_text += f'<h3>Work Period: {start_date} - {end_date}</h3>'
html_text += detail_table
html_text += '</body>\n</html>'

# Write Files
def write_file(name, data):
    f = open(name, "w")
    f.write(data)
    f.close()
    print(f"writing File: {name}")

print(f"Found {len(timecard_detail_data)} Timecard Records")

print('Writing Files')
path = "output"
csv_file = f"{path}/report.csv"
html_file = f"{path}/report.html"

write_file(csv_file, report_text)
write_file(html_file, html_text)
print(f'\nWrote Timecard CSV to {csv_file}')
print(f'Wrote Timecard HTML Report to {html_file}')

print(f'TOTAL HOURS:\n{total}')
