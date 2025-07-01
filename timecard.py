import pandas as pd
from datetime import date, timedelta, datetime
from html import escape
import os

VERSION = '0.2'
VER_DATE = '6/3/2025'
EXE = False
if EXE:
    INPUT_DIR = os.path.join(os.getcwd(), "timecard/input")
    OUTPUT_DIR = os.path.join(os.getcwd(), "timecard/output")
else:
    INPUT_DIR = os.path.join(os.getcwd(), "input")
    OUTPUT_DIR = os.path.join(os.getcwd(), "output")

CURRENT_YEAR = datetime.now().year  # TODO wont work with split year

def read_csv_files():
    timecard_detail_data = pd.read_csv(f"{INPUT_DIR}/approved_hours.csv", dtype=str)
    payroll_info = pd.read_csv(f"{INPUT_DIR}/payroll_info.csv", dtype=str)
    summary_hours = pd.read_csv(f"{INPUT_DIR}/summary_hours.csv", dtype=str)
    print("CSV files loaded.")
    return timecard_detail_data, payroll_info, summary_hours

def get_iso_week_dates(year: int, week: int) -> tuple[date, date]:
    """
    Returns the first (Monday) and last (Sunday) dates of a given ISO week.

    Args:
        year (int): The ISO year (e.g., 2025)
        week (int): The ISO week number (1–53)

    Returns:
        tuple: (first_day: date, last_day: date)
    """
    # ISO weekday: Monday=1, Sunday=7
    first_day = date.fromisocalendar(year, week, 1) - timedelta(days=1)
    last_day = first_day + timedelta(days=6)
    return first_day, last_day

def get_float(str):
    return float(str) if pd.notna(str) and str != '' else 0

def process_payroll_info(df):
    info = {}
    for row in df.to_dict('records'):
        emp_id = row['Employee #']
        info[emp_id] = {
            "hire_date": row['Hire Date'],
            "name": row['Name'],
            "title": row['Job Title'],
            "location": row['Location'],
            "schedule": row['Work Schedule'],
            "status": row['Employment Status'],
            "manager": row['Manager'],
        }
    return info


def process_timecard_detail(df):
    timecard_detail = {}
    start_week, min_day, max_day = 52, 20301231, 0
    min_date, max_date = 'NONE', 'NONE'

    for idx, row in enumerate(df.to_dict('records')):
        date_obj = datetime.strptime(row['Date'].split()[0], "%Y-%m-%d").date()
        # since Flockx starts work week one day earlier, calculate week # for one
        # day later
        one_day_later = date_obj + timedelta(days=1)
        week = one_day_later.isocalendar()[1]
        date_code = date_obj.year * 10000 + date_obj.month * 100 + date_obj.day

        start_week = min(start_week, week)
        if date_code < min_day:
            min_day, min_date = date_code, date_obj.strftime("%Y-%m-%d")
        if date_code > max_day:
            max_day, max_date = date_code, date_obj.strftime("%Y-%m-%d")

        timecard_detail[idx] = {
            'id': row['Employee Number'],
            'hours': float(row['Reg Hours']) if pd.notna(row['Reg Hours']) and
                row['Reg Hours'] != '' else 0,
            'date': date_obj.strftime("%Y-%m-%d"),
            'month': date_obj.month,
            'day': date_obj.day,
            'week': week + 1,
            'year': date_obj.year,
            'ot': float(row['OT Hours']) if pd.notna(row['OT Hours']) and
                row['OT Hours'] != '' else 0
        }

        # Compute Period Start / End based on min_date

    return timecard_detail, min_date, max_date, start_week


def process_summary_hours(df):
    timecard_summary = {}
    # zero out the data structure
    summary_cols = ['hours', 'ot', 'holiday', 'pto', 'personal',
                    'sick', 'other', 'total_pto', 'all_hrs']
    total = {key: 0 for key in summary_cols}

    for row in df.to_dict('records'):
        id = row['Employee Number']
        fields = [
            get_float(row.get('Regular', 0)),
            get_float(row.get('Overtime', 0)),
            get_float(row.get('Holiday', 0)),
            get_float(row.get('Paid Time Off}', 0)),
            get_float(row.get('Personal Day', 0)),
            get_float(row.get('Sick Leave', 0)) + get_float(row.get('Sick Leave (CA)', 0)),
            get_float(row.get('Bereavement', 0)) + get_float(row.get('Volunteer', 0)) + get_float(row.get('Voting', 0)),
            get_float(row.get('Total PTO', 0)),
            get_float(row.get('Total Hours', 0)),
        ]

        fields = [float(f) if pd.notna(f) and f != '' else 0 for f in fields]
        approved = row.get('Approved?', '')
        keys = summary_cols
        print(keys)
        print(fields)
        record = dict(zip(keys, fields))
        record['total_hrs'] = (record['hours'] + record['ot'] +
            record['holiday'] + record['personal'] + record['sick'] +
            record['other'] + record['pto'])
        record['approved'] = approved

        for key in total.keys():
            if key in record:
                total[key] += record[key]

        timecard_summary[id] = record

    return timecard_summary, total


def create_report(info, timecard_summary, timecard_detail, total, start_date, end_date, start_week):
    headers = ['Work Schedule', 'Emp Status', 'Location', 'Employee Name', 'Manager', 'Reg Hrs', 'OT Hrs', 'Hol Hrs', 'Pers Hrs']
    headers += ['Sick Hrs', 'Other PTO', 'Total PTO', 'Total Hrs', 'Approved?']

    # Compute Work Period from start_week
    per_start, unused = get_iso_week_dates(CURRENT_YEAR, start_week)
    unused, per_end = get_iso_week_dates(CURRENT_YEAR, start_week + 1)

    csv_lines = [','.join(headers)]
    html_rows = []

    for id, summary in timecard_summary.items():
        emp_info = info.get(id, {key: '*MISSING*' for key in ['schedule', 'status', 'location', 'name', 'manager']})
        row = [
            emp_info.get('schedule', '*MISSING*'),
            emp_info.get('status', '*MISSING*'),
            emp_info.get('location', '*MISSING*'),
            f'"{emp_info.get("name", "*MISSING*")}"',
            emp_info.get('manager', '*MISSING*'),
            f"{summary['hours']:.2f}",
            f"{summary['ot']:.2f}",
            f"{summary['holiday']:.2f}",
            f"{summary['personal']:.2f}",
            f"{summary['sick']:.2f}",
            f"{summary['other']:.2f}",
            f"{summary['pto']:.2f}",
            f"{summary['total_hrs']:.2f}",
            summary['approved']
        ]
        csv_lines.append(','.join(row))
        html_row = ''.join(f"<td>{escape(str(cell))}</td>" for cell in row)
        html_rows.append(f"<tr>{html_row}</tr>")

    style_section = """
    <style>
      table { border-collapse: collapse; }
      th, td {
                border: 1px solid black;
                border-collapse: collapse;
                padding-left: 10px; 
                padding-right: 10px; 
      }
      th { background-color: #aed6f1; }
    </style>
    """

    summary_table_html = f"""
    <h1>Timecard Report</h1>
    <h3>Hours Reported: {start_date} - {end_date}</h3>
    <table border="1" cellpadding="5">
      <tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr>
      {''.join(html_rows)}
    </table>
    """

    from collections import defaultdict

    # First group timecard detail entries by employee name and then by week
    name_week_grouped_details = defaultdict(lambda: defaultdict(list))
    for _, record in timecard_detail.items():
        emp_id = record['id']
        emp_name = info.get(emp_id, {}).get('name', '*MISSING*')
        week_num = record['week'] - start_week  # Relative week number
        record['name'] = emp_name
        name_week_grouped_details[emp_name][week_num].append(record)

    # Generate one detail table per employee, split by week
    detail_tables_by_name_week = []
    detail_headers = ['Emp #', 'Employee Name', 'Week', 'Date',
                      'Reg Hrs', 'OT Hrs', 'Total Hours']
    detailed_csv_file = [','.join(detail_headers)]

    for emp_name, week_groups in name_week_grouped_details.items():
        # Initialize employee-wide totals
        emp_reg_total = 0
        emp_ot_total = 0
        emp_sick_total = 0
        emp_total_total = 0

        for week_num in sorted(week_groups):
            rows_html = []
            # Initialize totals per week
            reg_total = 0
            ot_total = 0
            sick_total = 0
            total_total = 0

            for record in week_groups[week_num]:
                reg_hours = record['hours']
                ot_hours = record['ot']
                sick_hours = record.get('sick', 0) + record.get('sick_ca', 0)
                total_hours = reg_hours + ot_hours + sick_hours

                # Add to week totals
                reg_total += reg_hours
                ot_total += ot_hours
                sick_total += sick_hours
                total_total += total_hours

                # Also add to employee totals
                emp_reg_total += reg_hours
                emp_ot_total += ot_hours
                emp_sick_total += sick_hours
                emp_total_total += total_hours

                row = [
                    record['id'],
                    emp_name,
                    week_num,
                    record['date'],
                    f"{reg_hours:.2f}",
                    f"{ot_hours:.2f}",
                    f"{total_hours:.2f}"
                ]
                html_row = ''.join(
                    f"<td>{escape(str(cell))}</td>" for cell in row)
                rows_html.append(f"<tr>{html_row}</tr>")
                detailed_csv_file.append(','.join(f'"{cell}"' for cell in row))

            # Add a TOTAL row for the week
            total_row = [
                '', '', '', 'TOTAL:',
                f"{reg_total:.2f}",
                f"{ot_total:.2f}",
                f"{total_total:.2f}"
            ]
            total_html_row = ''.join(
                f"<td><strong>{escape(str(cell))}</strong></td>" for cell in
                total_row)
            rows_html.append(f"<tr>{total_html_row}</tr>")

            wk_start, week_end = get_iso_week_dates(CURRENT_YEAR, week_num + start_week - 1)
            table_html = f"""
            <h2>{escape(emp_name)} – Week {week_num} [{wk_start} - {week_end}]</h2>
            <table>
              <tr>{''.join(f'<th>{h}</th>' for h in detail_headers)}</tr>
              {''.join(rows_html)}
            </table><br>
            """
            detail_tables_by_name_week.append(table_html)

        # After all weeks for this employee, add an EMPLOYEE GRAND TOTAL table
        grand_total_html = f"""
        <h2>{escape(emp_name)} – Payroll Period Total [{per_start} - {per_end}]</h2>
        <table>
          <tr>{''.join(f'<th>{h}</th>' for h in detail_headers)}</tr>
          <tr>
            <td></td><td>{escape(emp_name)}</td><td></td><td><strong>TOTAL:</strong></td>
            <td><strong>{emp_reg_total:.2f}</strong></td>
            <td><strong>{emp_ot_total:.2f}</strong></td>
            <td><strong>{emp_total_total:.2f}</strong></td>
          </tr>
        </table><br>
        """
        detail_tables_by_name_week.append(grand_total_html)

    detail_table_html = f"""
    <h1>Timecard Details by Employee and Week</h1>
    <h3>Work Period: {per_start} - {per_end}</h3>
    {''.join(detail_tables_by_name_week)}
    """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Timecard Report</title>
    {style_section}
    </head>
    <body>
    <font size="2" face="Arial" >
    {summary_table_html}<br>{detail_table_html}
    </body></html>
    """

    return '\n'.join(csv_lines), full_html, '\n'.join(detailed_csv_file)


def write_file(filename, data):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"Wrote file: {filename}")


def main():
    timecard_detail_data, payroll_info, summary_hours = read_csv_files()

    info = process_payroll_info(payroll_info)
    timecard_detail, start_date, end_date, start_week = process_timecard_detail(timecard_detail_data)
    timecard_summary, total = process_summary_hours(summary_hours)

    print(f'Timecard Script: Version {VERSION} [{VER_DATE}]')
    print(f"Found {len(timecard_detail_data)} Timecard Records")

    csv_summary_file, html_report, csv_detail_file  = create_report(info, timecard_summary,
        timecard_detail, total, start_date, end_date, start_week)

    daterange = f"{start_date}_to_{end_date}"
    write_file(f"{OUTPUT_DIR}/summary_hours_{daterange}.csv", csv_summary_file)
    write_file(f"{OUTPUT_DIR}/detail_hours_{daterange}.csv", csv_detail_file)
    write_file(f"{OUTPUT_DIR}/timecard_report_{daterange}.html", html_report)

    print(f"\nTOTAL HOURS:")
    for key in total.keys():
        if total[key] > 0:
            print(f"{key}: {total[key]:.1f}")


if __name__ == "__main__":
    main()