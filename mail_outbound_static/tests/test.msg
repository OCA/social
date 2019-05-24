Delivered-To: test@gmail.com
Received: by 10.74.138.167 with SMTP id m36csp7226976ooj;
        Tue, 12 Sep 2017 10:37:56 -0700 (PDT)
X-Google-Smtp-Source: AOwi7QDKSb3BE6lIhVXub9wcPA/HxFKKpnNPconNr9f1L35SVw+EIm8itVQkbOdAW6TohImypmrF
X-Received: by 10.28.158.208 with SMTP id h199mr250060wme.47.1505237876258;
        Tue, 12 Sep 2017 10:37:56 -0700 (PDT)
ARC-Seal: i=1; a=rsa-sha256; t=1505237876; cv=none;
        d=google.com; s=arc-20160816;
        b=E2B6KUxHOJQk1YrT12BpitEMCgkxyqEXcFlwPWKjA/i/Xyvlh+09spNOF4VPmD/ZJm
         5lkY6hYyxvIH2RpRPeZVPkRIYhaEASkMIygdJu9Gd4weBdO2rd8iP/zSGHYyAmO/hLN2
         64hXtKexrWnO/YNWlpfhAo1kiwgSRVnZx55EopbWP49cy7BzKfwr1kHN0T9A5Lw1w+BW
         ZrXdCX6LRxHS2USKHb76PAVt0bhwsM/ZznBauR2zNKYcPxAWzdpN/vK3BDmWUdqbbSaB
         BOKINjuI9EmWynogDZE7Riu+sbc5QafE3owla1/2d0Bogp9FLtJe0YyQeW2qLvZKcmlI
         ftSQ==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20160816;
        h=to:list-archive:list-unsubscribe:list-subscribe:precedence
         :list-post:list-id:date:reply-to:from:subject:references:message-id
         :mime-version:arc-authentication-results;
        bh=DwvSiw5K7ryb4S8O/8HcIaGhJqbOxcXKsnPAr63iQZ4=;
        b=U0Ac9Rqvv+tfqO9fCx+F79oZknn3rOv9N9ekViEuL5DtjpJxKDDkO1xw//sV3eRILT
         nqGuxd2yQXwC4U+WAwraBwoLC3ScHb/9gWtzlrLCgv6WbNE7HZi5g6L8c0LWRN24cIe9
         AOdc/8fOdGoaL8yajrGEHgMz9B2KMltA9tZyxFOeKsyODxJ6iWjXcG1BSQTxERwosV3h
         ch8AznQr7xLLvc/u9VTEqC5ome3RqsxKRxOGenEqIbCOr11sxwpZQdQcNR6faNRom3+2
         6gz++4tVIV9cqYX1j9eEU/ufoUzBJ6Uzm0jMGZZQOHAF+YX3tZUEsPmc75PsvRCAIWby
         urMg==
ARC-Authentication-Results: i=1; mx.google.com;
       spf=pass (google.com: domain of postmaster-odoo@odoo-community.org designates 2a01:4f8:a0:430d::2 as permitted sender) smtp.mailfrom=postmaster-odoo@odoo-community.org;
       dmarc=fail (p=QUARANTINE sp=QUARANTINE dis=QUARANTINE) header.from=laslabs.com
Return-Path: <postmaster-odoo@odoo-community.org>
Received: from odoo-community.org (odoo-community.org. [2a01:4f8:a0:430d::2])
        by mx.google.com with ESMTP id j72si1795626wmg.60.2017.09.12.10.37.55
        for <test@gmail.com>;
        Tue, 12 Sep 2017 10:37:56 -0700 (PDT)
Received-SPF: pass (google.com: domain of postmaster-odoo@odoo-community.org designates 2a01:4f8:a0:430d::2 as permitted sender) client-ip=2a01:4f8:a0:430d::2;
Authentication-Results: mx.google.com;
       spf=pass (google.com: domain of postmaster-odoo@odoo-community.org designates 2a01:4f8:a0:430d::2 as permitted sender) smtp.mailfrom=postmaster-odoo@odoo-community.org;
       dmarc=fail (p=QUARANTINE sp=QUARANTINE dis=QUARANTINE) header.from=laslabs.com
Received: from odoo.odoo-community.org (localhost.localdomain [127.0.0.1])
	by odoo-community.org (Postfix) with ESMTP id DB5DC2EC2277;
	Tue, 12 Sep 2017 19:37:53 +0200 (CEST)
Content-Type: multipart/mixed; boundary="===============7439524030966430607=="
MIME-Version: 1.0
Message-Id: <A1AAECD6-2A36-45E1-A0F8-4266F178D52C@laslabs.com>
references: <0db43737-b846-4890-6801-44ff9617e3b3@camptocamp.com>
Subject: Re: OCA Code sprint: sprint topics
From: Dave Lasley <test@laslabs.com>
Reply-To: "Odoo Community Association \(OCA\) Contributors"
 <contributors@odoo-community.org>
Date: Tue, 12 Sep 2017 17:37:53 -0000
List-Id: contributors.odoo-community.org
List-Post: <mailto:contributors@odoo-community.org>
Precedence: list
X-Auto-Response-Suppress: OOF
List-Subscribe: <https://odoo-community.org/groups>
List-Unsubscribe: <https://odoo-community.org/groups?unsubscribe>
List-Archive: <https://odoo-community.org/groups/contributors-15>
To: "Contributors" <contributors@odoo-community.org>

--===============7439524030966430607==
Content-Type: multipart/alternative;
 boundary="===============8317593469411551167=="
MIME-Version: 1.0

--===============8317593469411551167==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

VGhpcyBpcyBhIGZha2UsIHRlc3QgbWVzc2FnZQ==
--===============7439524030966430607==--
