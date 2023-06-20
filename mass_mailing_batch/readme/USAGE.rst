In order to send 100 emails every 30 Minutes configure as follows:

1. Set the frequency of CRON "Process Mass Mailing Queue" to 30 Minutes;
2. Set the System Parameter `mass_mailing_batch.size` to 100;

after each CRON iteration, the Mass Mailing will be in state "Sending" as long as there are still emails to be sent.
