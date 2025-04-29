import pandas as pd
import datetime
from html import escape
import os

INPUT_DIR = "input"
OUTPUT_DIR = "output"


def read_csv_files():
    timecard_detail_data = pd.read_csv(f"{INPUT_DIR}/approved_hours.csv", dtype=str)
    payroll_info = pd.read_csv(f"{INPUT_DIR}/payroll_info.csv", dtype=str)
    summary_hours = pd.read_csv(f"{INPUT_DIR}/summary_hours.csv", dtype=str)
    print("CSV files loaded.")
    return timecard_detail_data, payroll_info, summary_hours


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
    start_week, start_day, end_day = 52, 20301231, 0
    start_date, end_date = 'NONE', 'NONE'

    for idx, row in enumerate(df.to_dict('records')):
        date_obj = datetime.datetime.strptime(row['Date'].split()[0], "%Y-%m-%d").date()
        week = date_obj.isocalendar()[1]
        datecode = date_obj.year * 10000 + date_obj.month * 100 + date_obj.day

        start_week = min(start_week, week)
        if datecode < start_day:
            start_day, start_date = datecode, date_obj.strftime("%Y-%m-%d")
        if datecode > end_day:
            end_day, end_date = datecode, date_obj.strftime("%Y-%m-%d")

        timecard_detail[idx] = {
            'id': row['Employee Number'],
            'hours': float(row['Reg Hours']) if pd.notna(row['Reg Hours']) and
                row['Reg Hours'] != '' else 0,
            'date': date_obj.strftime("%Y-%m-%d"),
            'month': date_obj.month,
            'day': date_obj.day,
            'week': week,
            'year': date_obj.year,
            'ot': float(row['OT Hours']) if pd.notna(row['OT Hours']) and
                row['OT Hours'] != '' else 0
        }
    return timecard_detail, start_date, end_date, start_week


def process_summary_hours(df):
    timecard_summary = {}
    total = {key: 0 for key in ['hours', 'ot', 'holiday', 'bereavement', 'personal',
                                'sick', 'sick_ca', 'vol', 'vote', 'pto', 'all_hrs']}

    for row in df.to_dict('records'):
        id = row['Employee Number']
        fields = [
            row.get('Regular', 0), row.get('Overtime', 0), row.get('Holiday', 0),
            row.get('Bereavement', 0), row.get('Personal Day', 0), row.get('Sick Leave', 0),
            row.get('Sick Leave (CA)', 0), row.get('Volunteer', 0), row.get('Voting', 0),
            row.get('Total PTO', 0)
        ]
        fields = [float(f) if pd.notna(f) and f != '' else 0 for f in fields]
        approved = row.get('Approved?', '')

        keys = ['hours', 'ot', 'holiday', 'bereavement', 'personal', 'sick', 'sick_ca', 'vol', 'vote', 'pto']
        record = dict(zip(keys, fields))
        record['total_hrs'] = record['hours'] + record['ot']
        record['approved'] = approved

        for k in total.keys():
            if k in record:
                total[k] += record[k]

        timecard_summary[id] = record

    return timecard_summary, total


def create_report(info, timecard_summary, timecard_detail, total, start_date, end_date, start_week):
    headers = ['Work Schedule', 'Emp Status', 'Location', 'Employee Name', 'Manager', 'Regular', 'OT', 'Holiday']
    optional_fields = [('sick', 'Sick'), ('sick_ca', 'Sick (CA)'), ('bereavement', 'Bereavement'), ('vol', 'Vol'), ('vote', 'Vote')]
    headers += [name for key, name in optional_fields if total[key] > 0.1]
    headers += ['Total PTO', 'Total Hrs', 'Approved?']

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
            str(summary['hours']),
            str(summary['ot']),
            str(summary['holiday'])
        ]

        for key, _ in optional_fields:
            if total[key] > 0.1:
                row.append(str(summary.get(key, 0)))

        row += [str(summary['pto']), str(summary['total_hrs']), summary['approved']]

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
      th { background-color: #f2f2f2; }
    </style>
    """

    summary_table_html = f"""
    <h1>Timecard Report</h1>
    <h3>Work Period: {start_date} - {end_date}</h3>
    <table border="1" cellpadding="5">
      <tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr>
      {''.join(html_rows)}
    </table>
    """

    detail_headers = ['Emp#', 'Employee Name', 'Week', 'Date', 'Regular Hours', 'OT Hours', 'Sick Hours', 'Total Hours']
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
    detail_headers = ['Employee Number', 'Employee Name', 'Week', 'Date',
                      'Reg Hours', 'OT Hours', 'Sick Hours', 'Total Hours']

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
                sick_hours = record.get('sick', 0)
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
                    f"{sick_hours:.2f}",
                    f"{total_hours:.2f}"
                ]
                html_row = ''.join(
                    f"<td>{escape(str(cell))}</td>" for cell in row)
                rows_html.append(f"<tr>{html_row}</tr>")

            # Add a TOTAL row for the week
            total_row = [
                '', '', '', 'TOTAL:',
                f"{reg_total:.2f}",
                f"{ot_total:.2f}",
                f"{sick_total:.2f}",
                f"{total_total:.2f}"
            ]
            total_html_row = ''.join(
                f"<td><strong>{escape(str(cell))}</strong></td>" for cell in
                total_row)
            rows_html.append(f"<tr>{total_html_row}</tr>")

            table_html = f"""
            <h2>{escape(emp_name)} – Week {week_num}</h2>
            <table>
              <tr>{''.join(f'<th>{h}</th>' for h in detail_headers)}</tr>
              {''.join(rows_html)}
            </table><br>
            """
            detail_tables_by_name_week.append(table_html)

        # After all weeks for this employee, add an EMPLOYEE GRAND TOTAL table
        grand_total_html = f"""
        <h2>{escape(emp_name)} – Payroll Period Total</h2>
        <table>
          <tr>{''.join(f'<th>{h}</th>' for h in detail_headers)}</tr>
          <tr>
            <td></td><td>{escape(emp_name)}</td><td></td><td><strong>TOTAL:</strong></td>
            <td><strong>{emp_reg_total:.2f}</strong></td>
            <td><strong>{emp_ot_total:.2f}</strong></td>
            <td><strong>{emp_sick_total:.2f}</strong></td>
            <td><strong>{emp_total_total:.2f}</strong></td>
          </tr>
        </table><br>
        """
        detail_tables_by_name_week.append(grand_total_html)

    detail_table_html = f"""
    <h1>Timecard Details by Employee and Week</h1>
    <h3>Work Period: {start_date} - {end_date}</h3>
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
    <body>{summary_table_html}<br>{detail_table_html}
    </body></html>
    """

    return '\n'.join(csv_lines), full_html


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

    print(f"Found {len(timecard_detail_data)} Timecard Records")

    csv_report, html_report = create_report(info, timecard_summary,
        timecard_detail, total, start_date, end_date, start_week)

    write_file(f"{OUTPUT_DIR}/report.csv", csv_report)
    write_file(f"{OUTPUT_DIR}/report.html", html_report)

    print(f"TOTAL HOURS: {total}")


if __name__ == "__main__":
    main()