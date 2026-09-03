Multi-company scope of the posts.
---------------

The accounts (`social.account`) and their daily statistics
(`social.account.statistics`) are the multi-company records: they carry a
company and a record rule that filters them. The posts and their publications
have neither a company field nor an equivalent rule, so they are only filtered
by their responsible user. In a multi-company database a social media
administrator therefore sees the posts of every company.


Limits of the social media, not of the account
---------------

The limits a post is checked against are those of the social media, not those
of the account. A paid plan can raise them — X Premium takes the message from
280 to 25 000 characters — and an account on such a plan is warned today about
a post it could publish. `_get_post_errors` already takes the account next to
the `media_type`, and the publication already passes it, so what is missing is
a connector able to tell the plan apart. Until then the checks err on the safe
side: a limit stricter than the one the account really has warns too much,
never too little, and it never blocks saving.


Counters of a publication without a synchronization module
---------------

`social.post.account` carries the six interaction counters, and nothing in
this module writes them: they are filled by an import, which lives in
*Social Media Sync*. Installed alone, this module shows them at zero, and the
card of an account whose social media reports no daily figures adds up to
zero as well. It is accurate — nobody asked the social media — but it reads
like a broken dashboard, and there is no way from here to tell the two apart.
