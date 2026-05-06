"""
reminder.py
-----------
Connects directly to the InfinityFree MySQL database and sends
class reminder emails — no external cron URL needed.

Run on PythonAnywhere scheduled tasks every 1 minute, or locally.

Requirements:
    pip install mysql-connector-python
"""

import smtplib
import logging
import sys
import os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import mysql.connector

# ── CONFIG (reads from environment variables set in GitHub Secrets) ───────────
DB_HOST = os.environ.get('DB_HOST', 'sql100.infinityfree.com')
DB_USER = os.environ.get('DB_USER', 'if0_41754243')
DB_PASS = os.environ.get('DB_PASS', 'Jelili20')
DB_NAME = os.environ.get('DB_NAME', 'if0_41754243_class_reminder')

MAIL_HOST       = os.environ.get('MAIL_HOST',       'smtp.gmail.com')
MAIL_PORT       = int(os.environ.get('MAIL_PORT',   '465'))
MAIL_USERNAME   = os.environ.get('MAIL_USERNAME',   'jeaytechhub@gmail.com')
MAIL_PASSWORD   = os.environ.get('MAIL_PASSWORD',   'ldoh mxba qfld cbjo')
MAIL_FROM_EMAIL = os.environ.get('MAIL_FROM_EMAIL', 'jeaytechhub@gmail.com')
MAIL_FROM_NAME  = os.environ.get('MAIL_FROM_NAME',  'Class Reminder')

TIMEZONE_OFFSET = 1   # Africa/Lagos = UTC+1
WINDOW_MINUTES  = 5   # ±5 min window around target time

# ── LOGGING ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('reminder.log', encoding='utf-8'),
    ]
)
log = logging.getLogger()

# ── EMAIL TEMPLATE ────────────────────────────────────────
def build_email(name, event, reminder_hours, event_type):
    date_label = event['event_date'].strftime('%A, %d %b %Y')
    if event_type == 'weekly':
        date_label += ' (Weekly)'

    start_label = event['start_time_str']
    end_label   = event['end_time_str']

    body = f"""
        <p>Dear <strong>{name}</strong>,</p>
        <p>This is a reminder that your class starts in
           <strong>{reminder_hours} hour(s)</strong>.
           Please be prepared and on time.</p>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;margin:16px 0">
            <tr>
                <td style="padding:8px 12px;color:#6b7280;font-weight:600;
                           width:36%;border-bottom:1px solid #e5e7eb">Course Code</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">
                    {event['course_code']}</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;color:#6b7280;font-weight:600;
                           border-bottom:1px solid #e5e7eb">Course Title</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">
                    {event['course_title']}</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;color:#6b7280;font-weight:600;
                           border-bottom:1px solid #e5e7eb">Date</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">
                    {date_label}</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;color:#6b7280;font-weight:600;
                           border-bottom:1px solid #e5e7eb">Time</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">
                    {start_label} – {end_label}</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;color:#6b7280;font-weight:600">Venue</td>
                <td style="padding:8px 12px">{event['venue']}</td>
            </tr>
        </table>
        <p>Good luck! 🎓</p>
    """

    year = datetime.now().year
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Class Reminder</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f3f4f6;padding:32px 0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%">
      <tr>
        <td style="background:#4f46e5;border-radius:12px 12px 0 0;
                   padding:28px 32px;text-align:center">
          <p style="margin:0;font-size:1.3rem;font-weight:700;color:#fff">
              {MAIL_FROM_NAME}</p>
          <p style="margin:6px 0 0;font-size:.85rem;color:#c7d2fe">
              Class Reminder</p>
        </td>
      </tr>
      <tr>
        <td style="background:#ffffff;padding:32px;
                   color:#111827;font-size:.93rem;line-height:1.7">
          {body}
        </td>
      </tr>
      <tr>
        <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                   border-radius:0 0 12px 12px;padding:18px 32px;
                   text-align:center;color:#9ca3af;font-size:.78rem">
          <p style="margin:0">&copy; {year} {MAIL_FROM_NAME}.
             This is an automated message, please do not reply.</p>
          <p style="margin:6px 0 0">Developed by Jeay Tech Hub</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    return html


# ── SEND EMAIL ────────────────────────────────────────────
def send_mail(to_email, to_name, subject, html_body):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'{MAIL_FROM_NAME} <{MAIL_FROM_EMAIL}>'
        msg['To']      = f'{to_name} <{to_email}>'

        plain = subject  # minimal plain text fallback
        msg.attach(MIMEText(plain,     'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html',  'utf-8'))

        with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT) as server:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM_EMAIL, to_email, msg.as_string())

        return True
    except Exception as e:
        log.error(f'    Mail error to {to_email}: {e}')
        return False


# ── LOG NOTIFICATION TO DB ────────────────────────────────
def log_notification(cursor, message, recipient_email, role='student'):
    cursor.execute(
        "INSERT INTO notifications (message, recipient_email, recipient_role) "
        "VALUES (%s, %s, %s)",
        (message, recipient_email, role)
    )


# ── NOTIFY STUDENTS ───────────────────────────────────────
def notify_students(conn, cursor, event, event_type, reminder_hours):
    cursor.execute(
        "SELECT name, email FROM students "
        "WHERE faculty_id=%s AND department_id=%s AND level_id=%s "
        "AND status='approved'",
        (event['faculty_id'], event['department_id'], event['level_id'])
    )
    students = cursor.fetchall()

    if not students:
        log.info(f"    → No approved students for {event['course_code']}. Skipping.")
        return

    sent = 0
    for s in students:
        subject = f"Reminder: {event['course_code']} starts in {reminder_hours} hour(s)"
        body    = build_email(s['name'], event, reminder_hours, event_type)
        if send_mail(s['email'], s['name'], subject, body):
            log_notification(cursor, subject, s['email'], 'student')
            conn.commit()
            sent += 1

    log.info(f"    → {event['course_code']}: {sent}/{len(students)} reminder(s) sent.")


# ── MAIN ──────────────────────────────────────────────────
def main():
    # Server time = UTC + offset
    now          = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
    target_dt    = now + timedelta(hours=0)   # reminder_hours read from DB below
    today_date   = now.date()
    today_day    = now.strftime('%A')          # e.g. "Tuesday"

    log.info('=== Reminder script started ===')
    log.info(f'Server time: {now.strftime("%Y-%m-%d %H:%M:%S")} | Day: {today_day}')

    # ── Connect to DB ─────────────────────────────────────
    try:
        db = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS,
            database=DB_NAME, charset='utf8mb4',
            connection_timeout=15
        )
        cursor = db.cursor(dictionary=True)
        log.info('DB connected.')
    except Exception as e:
        log.error(f'DB connection failed: {e}')
        sys.exit(1)

    # ── Read reminder_hours from settings ─────────────────
    cursor.execute(
        "SELECT setting_value FROM settings WHERE setting_key='reminder_hours'"
    )
    row            = cursor.fetchone()
    reminder_hours = max(1, int(row['setting_value'])) if row else 1

    target_dt   = now + timedelta(hours=reminder_hours)
    window_low  = target_dt - timedelta(minutes=WINDOW_MINUTES)
    window_high = target_dt + timedelta(minutes=WINDOW_MINUTES)

    log.info(
        f'reminder_hours={reminder_hours}h | '
        f'window: {window_low.strftime("%H:%M")}–{window_high.strftime("%H:%M")}'
    )

    # ── Helper: is a time within the window? ──────────────
    def in_window(time_value):
        """time_value is a datetime.timedelta from MySQL TIME column."""
        # MySQL TIME comes as timedelta
        if isinstance(time_value, timedelta):
            class_dt = datetime.combine(today_date, datetime.min.time()) + time_value
        else:
            class_dt = datetime.combine(today_date, time_value)
        return window_low <= class_dt <= window_high

    def fmt_time(time_value):
        if isinstance(time_value, timedelta):
            total = int(time_value.total_seconds())
            h, m  = divmod(total // 60, 60)
            ampm  = 'AM' if h < 12 else 'PM'
            h12   = h % 12 or 12
            return f'{h12:02d}:{m:02d} {ampm}'
        return time_value.strftime('%I:%M %p')

    # ── Weekly timetable ───────────────────────────────────
    log.info(f'--- Checking weekly timetable (day: {today_day}) ---')
    cursor.execute(
        "SELECT * FROM timetable "
        "WHERE status='active' AND day_of_week=%s "
        "AND (reminder_sent_date IS NULL OR reminder_sent_date < %s)",
        (today_day, today_date)
    )
    weekly = cursor.fetchall()
    log.info(f'Found {len(weekly)} active class(es) for today.')

    for cls in weekly:
        cls['start_time_str'] = fmt_time(cls['start_time'])
        cls['end_time_str']   = fmt_time(cls['end_time'])
        cls['event_date']     = datetime.combine(today_date, datetime.min.time())

        if not in_window(cls['start_time']):
            log.info(
                f"  Skipping: {cls['course_code']} at {cls['start_time_str']} "
                f"(outside window)"
            )
            continue

        log.info(f"  Processing: {cls['course_code']} at {cls['start_time_str']}")
        notify_students(db, cursor, cls, 'weekly', reminder_hours)

        # Mark reminder sent for today
        cursor.execute(
            "UPDATE timetable SET reminder_sent_date=%s WHERE id=%s",
            (today_date, cls['id'])
        )
        db.commit()

    # ── Special timetable ──────────────────────────────────
    log.info('--- Checking special timetable ---')
    cursor.execute(
        "SELECT * FROM special_timetable "
        "WHERE status='active' AND reminder_sent=0"
    )
    specials = cursor.fetchall()
    log.info(f'Found {len(specials)} special event(s) pending reminder.')

    for event in specials:
        event['start_time_str'] = fmt_time(event['start_time'])
        event['end_time_str']   = fmt_time(event['end_time'])

        event_date = event['event_date']  # already a date object from MySQL
        if isinstance(event_date, datetime):
            event_date = event_date.date()

        event['event_date'] = datetime.combine(event_date, datetime.min.time())

        if event_date != today_date or not in_window(event['start_time']):
            log.info(
                f"  Skipping: {event['course_code']} on {event_date} "
                f"at {event['start_time_str']} (wrong date or outside window)"
            )
            continue

        log.info(f"  Processing: {event['course_code']} on {event_date}")
        notify_students(db, cursor, event, 'special', reminder_hours)

        cursor.execute(
            "UPDATE special_timetable SET reminder_sent=1 WHERE id=%s",
            (event['id'],)
        )
        db.commit()

    cursor.close()
    db.close()
    log.info('=== Reminder script completed ===\n')


if __name__ == '__main__':
    main()
