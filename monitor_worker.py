"""Scheduled claim-monitor worker. Run as a separate long-lived process: python monitor_worker.py."""
import logging
import os
import smtplib
import time
from email.message import EmailMessage

import schedule

from claim_monitor import _get_monitor_conn, check_monitored_claim_for_updates

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
LOG = logging.getLogger('echo_mind.monitor_worker')


def send_notification(recipient, subject, body):
    host = os.getenv('SMTP_HOST')
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    sender = os.getenv('SMTP_FROM') or username
    if not (host and sender and recipient):
        return False
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.set_content(body)
    port = int(os.getenv('SMTP_PORT', '587'))
    with smtplib.SMTP(host, port, timeout=20) as server:
        if os.getenv('SMTP_STARTTLS', 'true').lower() == 'true':
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(message)
    return True


def run_monitor_cycle():
    conn = _get_monitor_conn()
    try:
        rows = conn.execute("SELECT id FROM claim_monitors WHERE status = 'active' ORDER BY id").fetchall()
        monitor_ids = [int(row['id']) for row in rows]
    finally:
        conn.close()
    for monitor_id in monitor_ids:
        try:
            result = check_monitored_claim_for_updates(monitor_id)
            if result.get('has_update'):
                LOG.info('Evidence update detected for monitor %s', monitor_id)
        except Exception:
            LOG.exception('Monitor check failed for id=%s', monitor_id)
    deliver_pending_notifications()


def deliver_pending_notifications():
    conn = _get_monitor_conn()
    try:
        rows = conn.execute("""
            SELECT n.id, n.summary, n.trigger_reason, n.new_verdict, n.new_score,
                   m.email, m.claim_text
            FROM monitor_notifications n JOIN claim_monitors m ON m.id = n.monitor_id
            WHERE n.email_sent_at IS NULL AND m.email IS NOT NULL AND m.email != ''
            ORDER BY n.id LIMIT 100
        """).fetchall()
        for row in rows:
            try:
                sent = send_notification(row['email'], 'Echo Mind: evidence update for a followed claim',
                    'Claim: ' + row['claim_text'] + '\n\n' + row['summary'] +
                    '\nCurrent assessment: ' + str(row['new_verdict']) +
                    ' (' + str(row['new_score']) + '/100).\n\nThis is an automated evidence-change alert, not a guarantee that the assessment is correct.')
                if sent:
                    conn.execute("UPDATE monitor_notifications SET email_sent_at = CURRENT_TIMESTAMP WHERE id = ?", (row['id'],))
            except Exception:
                LOG.exception('Notification delivery failed for notification id=%s', row['id'])
        conn.commit()
    finally:
        conn.close()


def main():
    interval = max(5, int(os.getenv('MONITOR_INTERVAL_MINUTES', '30')))
    LOG.info('Starting claim-monitor worker; interval=%s minutes', interval)
    schedule.every(interval).minutes.do(run_monitor_cycle)
    run_monitor_cycle()
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
