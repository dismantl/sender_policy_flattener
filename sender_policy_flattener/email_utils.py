# coding=utf-8
import smtplib
from difflib import HtmlDiff
from email import utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sender_policy_flattener.formatting import format_records_for_email

_email_style = """
    <style type="text/css">
        body {font-family: "Helvetica Neue Light", "Lucida Grande", "Calibri", "Arial", sans-serif;}
        a {text-decoration: none; color: royalblue; padding: 5px;}
        a:visited {color: royalblue}
        a:hover {background-color: royalblue; color: white;}
        h1 {
            font-family: "Helvetica Neue Light", "Lucida Grande", "Calibri", "Arial", sans-serif;
            font-size: 14pt;
        }
        table.diff {border: 1px solid black;}
        td {padding: 5px;}
        td.diff_header {text-align:right}
        .diff_header {background-color:#e0e0e0}
        .diff_next {background-color:#c0c0c0}
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}
    </style>
    """


def email_changes(
    zone,
    prev_addrs,
    curr_addrs,
    subject,
    server,
    fromaddr,
    password,
    toaddr,
    test=False,
):
    bindformat = format_records_for_email(curr_addrs)
    prev_addrs = " ".join(prev_addrs)
    curr_addrs = " ".join(curr_addrs)
    prev = sorted([s for s in prev_addrs.split() if "ip" in s])
    curr = sorted([s for s in curr_addrs.split() if "ip" in s])

    diff = HtmlDiff()
    table = diff.make_table(
        fromlines=prev, tolines=curr, fromdesc="Old records", todesc="New records"
    )

    header = "<h1>Diff</h1>"
    html = _email_style + bindformat + header + table
    html = MIMEText(html, "html")
    msg_template = MIMEMultipart("alternative")
    msg_template["From"] = fromaddr
    msg_template["To"] = toaddr
    msg_template["Subject"] = subject.format(zone=zone)
    msg_template["Date"] = utils.formatdate()
    msg_template["MIME-Version"] = "1.0"
    msg_template["Reply-To"] = fromaddr
    msg_template["X-Mailer"] = "Python smtplib"

    if "@" in fromaddr:
        msg_template["Message-ID"] = utils.make_msgid(
            domain=fromaddr.split("@")[1] or "example.com"
        )
    else:
        print(f"Invalid from address: {fromaddr}")

    email = msg_template
    email.attach(html)

    try:
        mailserver = smtplib.SMTP_SSL(server)

        # Verify the from address
        if not mailserver.verify(fromaddr):
            print(f"Invalid from address: {fromaddr}")
            return

        # Login if a password was provided
        if password:
            print("\nPassword detected, attempting to login to smtp server\n")
            mailserver.login(fromaddr, password)

        mailserver.sendmail(fromaddr, toaddr, email.as_string())
    except Exception as err:
        print("Email failed: " + str(err))
        with open("result.html", "w+") as mailfile:
            mailfile.write(html.as_string())
    if test:
        return bindformat
