* Navigate to an Outbound Email Server
* Set the `Email From` option to an email address
* If not email_from has been defined in any smtp server, the address can be obtained
  via the odoo.conf file, using the parameter email_from,
  Ex:

# specify the SMTP email address for sending email

email_from = example@server.com
