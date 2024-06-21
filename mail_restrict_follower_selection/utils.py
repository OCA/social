# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def _id_get(env, id_str):
    """Have a more secure ref function for use with safe_eval.

    Returning only the ID of the record.
    """
    return env.ref(id_str).id
