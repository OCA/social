To configure this module, you need to:

#. go to Settings/Technical/Parameters/System parameters to edit the value of ``mail_queue_send_limit.limit`` which is the amount of mails to send per queue run
#. edit your mail queue cronjob to run just as often that your SMTP server accepts the amount of mails you filled in above
