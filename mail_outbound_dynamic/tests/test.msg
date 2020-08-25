Delivered-To: katherine.zaoral@gmail.com
Received: by 2002:a0c:be03:0:0:0:0:0 with SMTP id k3csp5422954qvg;
        Tue, 25 Aug 2020 12:07:23 -0700 (PDT)
X-Google-Smtp-Source: ABdhPJzIBrepD8eBi7hb+Rp3TkM6l2IUB/GQ+F8vv2vmJliHCWurZAVha3cPupo4nodvuSC1lHne
X-Received: by 2002:a05:6638:1501:: with SMTP id b1mr6995395jat.93.1598382443253;
        Tue, 25 Aug 2020 12:07:23 -0700 (PDT)
ARC-Seal: i=1; a=rsa-sha256; t=1598382443; cv=none;
        d=google.com; s=arc-20160816;
        b=vLfnTF0Z2xTAZOcwOm+6lu02hbA630PwlQ/rp6NvWi1zbtcS191omkA0yhl0MwsZjz
         UuxAyIqoNInVU2g3oJwL57Vf4iBAew6+on5XBE9FH2czzGcD0sSJXLdxA56M3pjBtRkn
         /4GohfW3E9aP/TGp7zYNfSygRzKWE/stZcf1mpO61r3fv0CgDUvAfH0Ud1Ox8CpiN5nh
         oqZk5usmeyNBLmeek76J8Uqp58x+GO6Ty4NdSwANH7ZPi1ehVHjEHWWwYGauzkYfqwk6
         YmVl9KhFGyMuxxv51zjNekCPJAv8Huo4jCPUQ1eypJzKtVzMBeLE/0T8kn0zsQJ2yQa6
         t8IQ==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20160816;
        h=date:to:reply-to:from:subject:references:message-id:mime-version
         :sender:dkim-signature;
        bh=Su65ZkAqEHTCNTslz07KucLFOea+K4tyxVuexS8Z7a8=;
        b=ytJphXtcqlbOcClumBLnFBz5EQeHRBVNhXppdPhR8cY/mwEbPr63uhEX9Uvx/V/qYA
         wo3MPQHmnBvsz7sxhkl36/PJF/9sI7aFdSptHkY14ZjK5rvxt+uHv5fK7a+YLgqNXLa4
         6eL9Zqf8USs//JYnfPDmQt12BJlKMH8qwcMCjXO2UPGhQWyZ1cX1c7eSgQh20u9K+qEv
         Wo1a268W17r9rUAZe+Z1i+9TfHYV5H7mDQHjpQojOR86pCnGJGukXJ1F36WjXOkyn84p
         zelRoV5gse6WfHbqH18ZpasbZnUNK9K+bhEpJ/KFqJmBeOIEOmlcfF03jdVIBmfJDtSg
         k5mg==
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=fail header.i=@sandbox.mgsend.net header.s=mx header.b="nC/pjU0W";
       spf=pass (google.com: domain of bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net designates 159.135.228.62 as permitted sender) smtp.mailfrom="bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net";
       dmarc=fail (p=NONE sp=NONE dis=NONE) header.from=adhoc.com.ar
Return-Path: <bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net>
Received: from m228-62.mailgun.net (m228-62.mailgun.net. [159.135.228.62])
        by mx.google.com with UTF8SMTPS id c204si7392420iof.89.2020.08.25.12.07.23
        for <katherine.zaoral@gmail.com>
        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);
        Tue, 25 Aug 2020 12:07:23 -0700 (PDT)
Received-SPF: pass (google.com: domain of bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net designates 159.135.228.62 as permitted sender) client-ip=159.135.228.62;
Authentication-Results: mx.google.com;
       dkim=fail header.i=@sandbox.mgsend.net header.s=mx header.b="nC/pjU0W";
       spf=pass (google.com: domain of bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net designates 159.135.228.62 as permitted sender) smtp.mailfrom="bounce+b698b5.ff1915-katherine.zaoral=gmail.com@sandbox.mgsend.net";
       dmarc=fail (p=NONE sp=NONE dis=NONE) header.from=adhoc.com.ar
DKIM-Signature: a=rsa-sha256; v=1; c=relaxed/relaxed; d=sandbox.mgsend.net; q=dns/txt; s=mx; t=1598382443; h=Date: To: Reply-To: From: Subject: references: Message-Id: MIME-Version: Content-Type: Sender; bh=Su65ZkAqEHTCNTslz07KucLFOea+K4tyxVuexS8Z7a8=; b=nC/pjU0WAVfiIbPMdBHp3xAW6qt5uSSA00olY3ObRaSiWBBovApdH7jX3jlgprJCaigftDfo 6Vyuf2pvW1GZnSP24MbHRVFxSC2T9MSXBXXky8HMFBFBG0u+qc9i2CbLWPPXOGRiu4mvYvDA il6WT0s73IEIG66TUf1/9qsXQL76vI/uiafB20GclIAYr0QnzLTW1fhTkDSD+GEMhQHwepms lSml1vvtP+ryZ42nxukp3UwrTHkSvtbVEKjXH3w6wf7BqiFECtV6/IOWpSkoN2OCVo6xRJbX SfIbTlUV5tKbm+whkgtPJBPq45KoHOr3oG+3eRZgHOoCn2fLDj7mDw==
X-Mailgun-Sending-Ip: 159.135.228.62
X-Mailgun-Sid: WyJjMjIzYiIsICJrYXRoZXJpbmUuemFvcmFsQGdtYWlsLmNvbSIsICJmZjE5MTUiXQ==
Received: from [172.17.0.6] (2-40-166-181.fibertel.com.ar [181.166.40.2]) by smtp-out-n02.prod.us-west-2.postgun.com with SMTP id 5f45616a76c283d04f1b205f; Tue, 25 Aug 2020 19:07:22 GMT
Sender: notifications=adhoc.com.ar@sandbox.mgsend.net
Content-Type: multipart/mixed; boundary="===============3019754856862731290=="
MIME-Version: 1.0
Message-Id: <459903915014427.1598382440.151133537292480-openerp-3-helpdesk.ticket@3228f3aa7ae8>
references: <079492216266670.1598382440.044920921325684-openerp-3-helpdesk.ticket@3228f3aa7ae8>
Subject: TICKET 1 (#3)
From: Mitchell Admin <admin@yourcompany.example.com>
Reply-To: Mitchell Admin <admin@yourcompany.example.com>
To: Kathy Gmail <katherine.zaoral@gmail.com>
Date: Tue, 25 Aug 2020 19:07:21 -0000
X-Odoo-Objects: helpdesk.ticket-3

--===============3019754856862731290==
Content-Type: multipart/alternative; boundary="===============6511330286069473333=="
MIME-Version: 1.0

--===============6511330286069473333==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

WW91ciBIZWxwZGVzayBUaWNrZXQKClRJQ0tFVCAxICgjMykKCgoKCgoKCkRlYXIgS2F0aHkgR21h
aWwsCgpZb3VyIHJlcXVlc3QKVElDS0VUIDEgWzFdCmhhcyBiZWVuIHJlY2VpdmVkIGFuZCBpcyBi
ZWluZyByZXZpZXdlZCBieSBvdXIgVEVBTSAxIHRlYW0uClRoZSByZWZlcmVuY2Ugb2YgeW91ciB0
aWNrZXQgaXMgMy4KCgpWaWV3IHRoZSB0aWNrZXQgWzJdCgpUbyBhZGQgYWRkaXRpb25hbCBjb21t
ZW50cywgcmVwbHkgdG8gdGhpcyBlbWFpbC4KClRoYW5rIHlvdSwKClRFQU0gMSBUZWFtLgoKCgoK
KihBUikgUmVzcG9uc2FibGUgSW5zY3JpcHRvKgoKKzEgNTU1IDEyMyA4MDY5CnwKaW5mb0BleGFt
cGxlLmNvbSBbM10KfApodHRwOi8vd3d3LmV4YW1wbGUuY29tCls0XQoKCgoKUG93ZXJlZCBieSBP
ZG9vIFs1XQoKCgpbMV0gaHR0cDovL29kb28xMy5sb2MvbXkvdGlja2V0LzMvYmI0MGJkNjQtYTA5
Mi00YzgxLWE2NzAtOTI4MmRmZDJkODNlClsyXSBodHRwOi8vb2RvbzEzLmxvYy9teS90aWNrZXQv
Mz9hY2Nlc3NfdG9rZW49YmI0MGJkNjQtYTA5Mi00YzgxLWE2NzAtOTI4MmRmZDJkODNlClszXSBt
YWlsdG86aW5mb0BleGFtcGxlLmNvbQpbNF0gaHR0cDovL3d3dy5leGFtcGxlLmNvbQpbNV0gaHR0
cHM6Ly93d3cub2Rvby5jb20/dXRtX3NvdXJjZT1kYiZ1dG1fbWVkaXVtPWVtYWls
--===============6511330286069473333==
Content-Type: text/html; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

Cjx0YWJsZSBib3JkZXI9IjAiIGNlbGxwYWRkaW5nPSIwIiBjZWxsc3BhY2luZz0iMCIgc3R5bGU9
InBhZGRpbmctdG9wOiAxNnB4OyBiYWNrZ3JvdW5kLWNvbG9yOiAjRjFGMUYxOyBmb250LWZhbWls
eTpWZXJkYW5hLCBBcmlhbCxzYW5zLXNlcmlmOyBjb2xvcjogIzQ1NDc0ODsgd2lkdGg6IDEwMCU7
IGJvcmRlci1jb2xsYXBzZTpzZXBhcmF0ZTsiPjx0cj48dGQgYWxpZ249ImNlbnRlciI+Cjx0YWJs
ZSBib3JkZXI9IjAiIGNlbGxwYWRkaW5nPSIwIiBjZWxsc3BhY2luZz0iMCIgd2lkdGg9IjU5MCIg
c3R5bGU9InBhZGRpbmc6IDI0cHg7IGJhY2tncm91bmQtY29sb3I6IHdoaXRlOyBjb2xvcjogIzQ1
NDc0ODsgYm9yZGVyLWNvbGxhcHNlOnNlcGFyYXRlOyI+Cjx0Ym9keT4KICAgIDx0cj4KICAgICAg
ICA8dGQgYWxpZ249ImNlbnRlciIgc3R5bGU9Im1pbi13aWR0aDogNTkwcHg7Ij4KICAgICAgICAg
ICAgPHRhYmxlIGJvcmRlcj0iMCIgY2VsbHBhZGRpbmc9IjAiIGNlbGxzcGFjaW5nPSIwIiB3aWR0
aD0iMTAwJSIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6IHdoaXRlOyBwYWRkaW5nOiAwOyBib3Jk
ZXItY29sbGFwc2U6c2VwYXJhdGU7Ij4KICAgICAgICAgICAgICAgIDx0cj48dGQgdmFsaWduPSJt
aWRkbGUiPgogICAgICAgICAgICAgICAgICAgIDxzcGFuIHN0eWxlPSJmb250LXNpemU6IDEwcHg7
Ij5Zb3VyIEhlbHBkZXNrIFRpY2tldDwvc3Bhbj48YnIvPgogICAgICAgICAgICAgICAgICAgIDxz
cGFuIHN0eWxlPSJmb250LXNpemU6IDIwcHg7IGZvbnQtd2VpZ2h0OiBib2xkOyI+CiAgICAgICAg
ICAgICAgICAgICAgICAgIFRJQ0tFVCAxICgjMykKICAgICAgICAgICAgICAgICAgICA8L3NwYW4+
CiAgICAgICAgICAgICAgICA8L3RkPjx0ZCB2YWxpZ249Im1pZGRsZSIgYWxpZ249InJpZ2h0Ij4K
ICAgICAgICAgICAgICAgICAgICA8aW1nIHN0eWxlPSJwYWRkaW5nOiAwcHg7IG1hcmdpbjogMHB4
OyBoZWlnaHQ6IDQ4cHg7IiBzcmM9Imh0dHA6Ly9vZG9vMTMubG9jL2xvZ28ucG5nP2NvbXBhbnk9
NCIgYWx0PSIoQVIpIFJlc3BvbnNhYmxlIEluc2NyaXB0byIvPgogICAgICAgICAgICAgICAgPC90
ZD48L3RyPgogICAgICAgICAgICAgICAgPHRyPjx0ZCBjb2xzcGFuPSIyIiBzdHlsZT0idGV4dC1h
bGlnbjpjZW50ZXI7Ij4KICAgICAgICAgICAgICAgICAgPGhyIHdpZHRoPSIxMDAlIiBzdHlsZT0i
YmFja2dyb3VuZC1jb2xvcjpyZ2IoMjA0LDIwNCwyMDQpO2JvcmRlcjptZWRpdW0gbm9uZTtjbGVh
cjpib3RoO2Rpc3BsYXk6YmxvY2s7Zm9udC1zaXplOjBweDttaW4taGVpZ2h0OjFweDtsaW5lLWhl
aWdodDowOyBtYXJnaW46NHB4IDBweCAzMnB4IDBweDsiLz4KICAgICAgICAgICAgICAgIDwvdGQ+
PC90cj4KICAgICAgICAgICAgPC90YWJsZT4KICAgICAgICA8L3RkPgogICAgPC90cj4KICAgIDx0
cj4KICAgICAgICA8dGQgc3R5bGU9Im1pbi13aWR0aDogNTkwcHg7Ij4KICAgICAgICAgICAgPGRp
dj4KICAgIERlYXIgS2F0aHkgR21haWwsPGJyPjxicj4KICAgIFlvdXIgcmVxdWVzdAogICAgPGEg
aHJlZj0iaHR0cDovL29kb28xMy5sb2MvbXkvdGlja2V0LzMvYmI0MGJkNjQtYTA5Mi00YzgxLWE2
NzAtOTI4MmRmZDJkODNlIj5USUNLRVQgMTwvYT4KICAgIGhhcyBiZWVuIHJlY2VpdmVkIGFuZCBp
cyBiZWluZyByZXZpZXdlZCBieSBvdXIgVEVBTSAxIHRlYW0uCiAgICBUaGUgcmVmZXJlbmNlIG9m
IHlvdXIgdGlja2V0IGlzIDMuPGJyPjxicj4KCiAgICA8ZGl2IHN0eWxlPSJ0ZXh0LWFsaWduOmNl
bnRlcjsgbWFyZ2luOjE2cHggMHB4IDE2cHggMHB4Ij4KICAgICAgICA8YSBzdHlsZT0iYmFja2dy
b3VuZC1jb2xvcjojODc1QTdCOyBwYWRkaW5nOjhweCAxNnB4IDhweCAxNnB4OyB0ZXh0LWRlY29y
YXRpb246bm9uZTsgY29sb3I6I2ZmZjsgYm9yZGVyLXJhZGl1czo1cHg7IGZvbnQtc2l6ZToxM3B4
IiBocmVmPSJodHRwOi8vb2RvbzEzLmxvYy9teS90aWNrZXQvMz9hY2Nlc3NfdG9rZW49YmI0MGJk
NjQtYTA5Mi00YzgxLWE2NzAtOTI4MmRmZDJkODNlIj5WaWV3IHRoZSB0aWNrZXQ8L2E+PGJyPgog
ICAgPC9kaXY+CgogICAgVG8gYWRkIGFkZGl0aW9uYWwgY29tbWVudHMsIHJlcGx5IHRvIHRoaXMg
ZW1haWwuPGJyPjxicj4KCiAgICBUaGFuayB5b3UsPGJyPjxicj4KICAgIFRFQU0gMSBUZWFtLgo8
L2Rpdj4KICAgICAgICAKICAgICAgICA8L3RkPgogICAgPC90cj4KICAgIDx0cj4KICAgICAgICA8
dGQgYWxpZ249ImNlbnRlciIgc3R5bGU9Im1pbi13aWR0aDogNTkwcHg7IHBhZGRpbmc6IDAgOHB4
IDAgOHB4OyBmb250LXNpemU6MTFweDsiPgogICAgICAgICAgICA8aHIgd2lkdGg9IjEwMCUiIHN0
eWxlPSJiYWNrZ3JvdW5kLWNvbG9yOnJnYigyMDQsMjA0LDIwNCk7Ym9yZGVyOm1lZGl1bSBub25l
O2NsZWFyOmJvdGg7ZGlzcGxheTpibG9jaztmb250LXNpemU6MHB4O21pbi1oZWlnaHQ6MXB4O2xp
bmUtaGVpZ2h0OjA7IG1hcmdpbjogMTZweCAwcHggNHB4IDBweDsiLz4KICAgICAgICAgICAgPGI+
KEFSKSBSZXNwb25zYWJsZSBJbnNjcmlwdG88L2I+PGJyLz4KICAgICAgICAgICAgPGRpdiBzdHls
ZT0iY29sb3I6ICM5OTk5OTk7Ij4KICAgICAgICAgICAgICAgICsxIDU1NSAxMjMgODA2OQogICAg
ICAgICAgICAgICAgIHwKICAgICAgICAgICAgICAgICAgICA8YSBzdHlsZT0idGV4dC1kZWNvcmF0
aW9uOm5vbmU7IGNvbG9yOiAjOTk5OTk5OyIgaHJlZj0ibWFpbHRvOmluZm9AZXhhbXBsZS5jb20i
PmluZm9AZXhhbXBsZS5jb208L2E+CiAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICB8
CiAgICAgICAgICAgICAgICAgICAgPGEgc3R5bGU9InRleHQtZGVjb3JhdGlvbjpub25lOyBjb2xv
cjogIzk5OTk5OTsiIGhyZWY9Imh0dHA6Ly93d3cuZXhhbXBsZS5jb20iPgogICAgICAgICAgICAg
ICAgICAgICAgICBodHRwOi8vd3d3LmV4YW1wbGUuY29tCiAgICAgICAgICAgICAgICAgICAgPC9h
PgogICAgICAgICAgICAgICAgCiAgICAgICAgICAgIDwvZGl2PgogICAgICAgIDwvdGQ+CiAgICA8
L3RyPgo8L3Rib2R5Pgo8L3RhYmxlPgo8L3RkPjwvdHI+Cjx0cj48dGQgYWxpZ249ImNlbnRlciIg
c3R5bGU9Im1pbi13aWR0aDogNTkwcHg7Ij4KICAgICAgICBQb3dlcmVkIGJ5IDxhIHRhcmdldD0i
X2JsYW5rIiBocmVmPSJodHRwczovL3d3dy5vZG9vLmNvbT91dG1fc291cmNlPWRiJmFtcDt1dG1f
bWVkaXVtPWVtYWlsIiBzdHlsZT0iY29sb3I6ICM4NzVBN0I7Ij5PZG9vPC9hPgo8L3RkPjwvdHI+
CjwvdGFibGU+CiAgICAgICAg
--===============6511330286069473333==--
--===============3019754856862731290==--
