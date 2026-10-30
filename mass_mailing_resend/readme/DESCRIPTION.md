A frequent need for users of mass mailings is to resend one mailing that
has already been sent in the past to new recipients that haven't
received yet that mail. But the problem is to know which are the
applicable ones.

Odoo already includes a method in its mass mailing logic that avoids to
resend the same mail 2 times for one mass mailing, and for v9, there was
a trick that allows to modify the state of a mass mailing from kanban
view, covering the need.

But now since v10 both status bar in form view and dragging between
states in kanban are not allowed.

This module introduces a button to restart a mass mailing to draft
state, allowing you to reevaluate the sending domain or list for
performing again the mailing.
