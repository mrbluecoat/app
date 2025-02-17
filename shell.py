from time import sleep

import flask_migrate
from IPython import embed
from sqlalchemy_utils import create_database, database_exists, drop_database

from app.config import DB_URI
from app.db import Session
from app.email_utils import send_email, render
from app.log import LOG
from app.models import (
    User,
    Mailbox,
)
from job_runner import (
    onboarding_pgp,
    onboarding_browser_extension,
    onboarding_mailbox,
    onboarding_send_from_alias,
)


def create_db():
    if not database_exists(DB_URI):
        LOG.d("db not exist, create database")
        create_database(DB_URI)

        # Create all tables
        # Use flask-migrate instead of db.create_all()
        flask_migrate.upgrade()


def change_password(user_id, new_password):
    user = User.get(user_id)
    user.set_password(new_password)
    Session.commit()


def reset_db():
    if database_exists(DB_URI):
        drop_database(DB_URI)
    create_db()


def send_mailbox_newsletter():
    for user in User.order_by(User.id).all():
        if user.notification and user.activated:
            try:
                LOG.d("Send newsletter to %s", user)
                send_email(
                    user.email,
                    "Introducing Mailbox - our most requested feature",
                    render("com/newsletter/mailbox.txt", user=user),
                    render("com/newsletter/mailbox.html", user=user),
                )
                sleep(1)
            except Exception:
                LOG.w("Cannot send to user %s", user)


def send_pgp_newsletter():
    for user in User.order_by(User.id).all():
        if user.notification and user.activated:
            try:
                LOG.d("Send PGP newsletter to %s", user)
                send_email(
                    user.email,
                    "Introducing PGP - encrypt your emails so only you can read them",
                    render("com/newsletter/pgp.txt", user=user),
                    render("com/newsletter/pgp.html", user=user),
                )
                sleep(1)
            except Exception:
                LOG.w("Cannot send to user %s", user)


def send_mobile_newsletter():
    count = 0
    for user in User.order_by(User.id).all():
        if user.notification and user.activated:
            count += 1
            try:
                LOG.d("#%s: send to %s", count, user)
                send_email(
                    user.email,
                    "Mobile and Dark Mode",
                    render("com/newsletter/mobile-darkmode.txt", user=user),
                    render("com/newsletter/mobile-darkmode.html", user=user),
                )
            except Exception:
                LOG.w("Cannot send to user %s", user)

            if count % 5 == 0:
                # sleep every 5 sends to avoid hitting email limits
                LOG.d("Sleep 1s")
                sleep(1)


def disable_mailbox(mailbox_id):
    """disable a mailbox and all of its aliases"""
    mailbox = Mailbox.get(mailbox_id)
    mailbox.verified = False
    for alias in mailbox.aliases:
        alias.enabled = False

    Session.commit()

    email_msg = f"""Hi,

    Your mailbox {mailbox.email} cannot receive emails.
    To avoid forwarding emails to an invalid mailbox, we have disabled this mailbox along with all of its aliases.

    If this is a mistake, please reply to this email.

    Thanks,
    SimpleLogin team.
                """

    try:
        send_email(
            mailbox.user.email,
            f"{mailbox.email} is disabled",
            email_msg,
            email_msg.replace("\n", "<br>"),
        )
    except Exception:
        LOG.e("Cannot send disable mailbox email to %s", mailbox.user)


def send_onboarding_emails(user):
    onboarding_send_from_alias(user)
    onboarding_mailbox(user)
    onboarding_browser_extension(user)
    onboarding_pgp(user)


if __name__ == "__main__":
    # to test email template
    # with open("/tmp/email.html", "w") as f:
    #     user = User.first()
    #     f.write(
    #         render(
    #             "transactional/reset-password.html",
    #             email=user.email,
    #             user=user,
    #             name=user.name,
    #             activation_link="https://ab.cd",
    #             alias="alias@ab.cd",
    #             directory="dir",
    #             domain="domain",
    #             new_email="new@email.com",
    #             current_email="current@email.com",
    #             link="https://link.com",
    #             mailbox_email="mailbox_email@email.com",
    #             sender="sender@example.com",
    #             reset_password_link="http://reset_password_link",
    #         )
    #     )

    embed()
