from google.appengine.api import mail


def send_email():
    message = mail.EmailMessage(sender="grocshare-0408.com Support <sharegroc@gmail.com>",
                                subject="Your order has been placed")

    message.to = "Sriram S V <sriramsv1991@gmail.com>"
    message.body = """ Your order has been placed"""

    message.send()
