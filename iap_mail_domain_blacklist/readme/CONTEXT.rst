Odoo can't add certain domains to the _MAIL_DOMAIN_BLACKLIST, which can result in incorrectly  
assuming that users with one of these specific domains belong to the same organization.  

For example, since outlook.jp is not part of _MAIL_DOMAIN_BLACKLIST, when partners have this  
same domain and create helpdesk tickets, they may end up sharing partners and mistakenly  
assuming ownership of each other's tickets.
