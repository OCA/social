/* Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

/* This JS module replaces core AJAX submission because it is impossible
 * to extend it as it is currently designed. It is almost a copy+paste from
 * upstream, to allow easier version/patch updates, so linter is disabled
 * and prettier is ignore. */
/* eslint-disable */
// prettier-ignore
odoo.define("mass_mailing_custom_unsubscribe.unsubscribe", function (require) {
    "use strict";

    var session = require('web.session');
    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');

    var _t = core._t;

    var email = $("input[name='email']").val();
    var mailing_id = parseInt($("input[name='mailing_id']").val(), 10);
    var res_id = parseInt($("input[name='res_id']").val(), 10);
    var token = (location.search.split('token' + '=')[1] || '').split('&')[0];
    var $mailing_lists = $("input[name='contact_ids']");
    var $reasons = $("#custom_div_feedback");
    var $details = $("textarea[name='details']");
    var $radio = $(":radio");
    var $info_state = $("#info_state, #custom_div_feedback");

    if (!$('.o_unsubscribe_form').length) {
        return Promise.reject("DOM doesn't contain '.o_unsubscribe_form'");
    }
    $radio.on('change click', function (e) {
        $details.prop(
            'required',
            $(e.target).is('[data-details-required]') && $(e.target).is(':visible')
        );
    });

    // Display reasons form only if there are unsubscriptions
    var toggle_reasons = function () {
        // Find contacts that were checked and now are unchecked
        var $disabled = $mailing_lists.filter(function () {
            var $this = $(this);
            return !$this.prop('checked') && $this.attr('checked');
        });
        // Hide reasons form if you are only subscribing
        $reasons.toggleClass('d-none', !$disabled.length);
        var $radios = $reasons.find(':radio');
        if ($reasons.is(':hidden')) {
            // Uncheck chosen reason
            $radios
                .prop('checked', false)
                // Unrequire specifying a reason
                .prop('required', false)
                // Remove possible constraints for details
                .trigger('change');
            // Clear textarea
            $details.val('');
        } else {
            // Require specifying a reason
            $radios.prop('required', true);
        }
    };
    $mailing_lists.change(function (e) {
        toggle_reasons();
        $('#info_state').addClass('invisible');
    });

    session.load_translations().then(function () {
        if (email != '' && email != undefined){
            ajax.jsonRpc('/mailing/blacklist/check', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#button_add_blacklist').hide();
                        $('#button_remove_blacklist').hide();
                    }
                    else if (result == true) {
                        $('#button_remove_blacklist').show();
                        toggle_opt_out_section(false);
                    }
                    else if (result == false) {
                        $('#button_add_blacklist').show();
                        toggle_opt_out_section(true);
                    }
                    else {
                        $('#subscription_info').html(_t('An error occurred. Please try again later or contact us.'));
                        $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
                    }
                })
                .guardedCatch(function () {
                    $('#subscription_info').html(_t('An error occurred. Please try again later or contact us.'));
                    $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
                });
        }
        else {
            $('#div_blacklist').hide();
        }

        var unsubscribed_list = $("input[name='unsubscribed_list']").val();
        if (unsubscribed_list){
            $('#subscription_info').html(_.str.sprintf(
                _t("You have been <strong>successfully unsubscribed from %s</strong>."),
                _.escape(unsubscribed_list)
            ));
        }
        else{
            $('#subscription_info').html(_t('You have been <strong>successfully unsubscribed</strong>.'));
        }
    });

    $('#unsubscribe_form').on('submit', function (e) {
        e.preventDefault();

        var checked_ids = [];
        $("input[type='checkbox']:checked").each(function (i) {
          checked_ids[i] = parseInt($(this).val(), 10);
        });

        var unchecked_ids = [];
        $("input[type='checkbox']:not(:checked)").each(function (i) {
          unchecked_ids[i] = parseInt($(this).val(), 10);
        });

        var values = {
            opt_in_ids: checked_ids,
            opt_out_ids: unchecked_ids,
            email: email,
            mailing_id: mailing_id,
            res_id: res_id,
            token: token,
        };
        // Only send reason and details if an unsubscription was found
        if ($reasons.is(':visible')) {
            values.reason_id = parseInt(
                $reasons.find("[name='reason_id']:checked").val(), 10
            );
            values.details = $details.val();
        }

        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', values)
            .then(function (result) {
                if (result == 'unauthorized'){
                    $('#subscription_info').html(_t('You are not authorized to do this!'));
                    $('#info_state').removeClass('invisible');
                    $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-error').addClass('alert-warning');
                }
                else if (result == true) {
                    $('#subscription_info').html(_t('Your changes have been saved.'));
                    $('#info_state').removeClass('invisible');
                    $info_state.removeClass('alert-info').addClass('alert-success');
                    // Store checked status, to enable further changes
                    $mailing_lists.each(function () {
                        var $this = $(this);
                        $this.attr('checked', $this.prop('checked'));
                    });
                    toggle_reasons();
                }
                else {
                    $('#subscription_info').html(_t('An error occurred. Your changes have not been saved, try again later.'));
                    $('#info_state').removeClass('invisible');
                    $info_state.removeClass('alert-info').addClass('alert-warning');
                }
            })
            .guardedCatch(function () {
                $('#subscription_info').html(_t('An error occurred. Your changes have not been saved, try again later.'));
                $('#info_state').removeClass('invisible');
                $info_state.removeClass('alert-info').addClass('alert-warning');
            });
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist').click(function (e) {
        e.preventDefault();

        if ($reasons.is(':hidden')) {
            $reasons.toggleClass('d-none', false);
            $reasons.find(':radio').prop('required', true);
        }
        if (!$('#unsubscribe_form')[0].reportValidity()) {
            return;
        }

        ajax.jsonRpc('/mailing/blacklist/add', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token,
            'reason_id': parseInt($reasons.find("[name='reason_id']:checked").val(), 10),
            'details': $details.val(),
        })
            .then(function (result) {
                if (result == 'unauthorized'){
                    $('#subscription_info').html(_t('You are not authorized to do this!'));
                    $('#info_state').removeClass('invisible');
                    $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-error').addClass('alert-warning');
                }
                else
                {
                    if (result) {
                        $('#subscription_info').html(_t('You have been successfully <strong>added to our blacklist</strong>. '
                               + 'You will not be contacted anymore by our services.'));
                        $('#info_state').removeClass('invisible');
                        $info_state.removeClass('alert-warning').removeClass('alert-info').removeClass('alert-error').addClass('alert-success');
                        toggle_opt_out_section(false);
                        // set mailing lists checkboxes to previous state
                        $mailing_lists.each(function () {
                            var $this = $(this);
                            $this.prop('checked', $(this)[0].hasAttribute('checked'));
                        });
                        // Hide reasons and reset reason fields
                        $reasons.toggleClass('d-none', true).find(':radio').prop('checked', false);
                        $details.val('').prop('required', false);
                    }
                    else {
                        $('#subscription_info').html(_t('An error occurred. Please try again later or contact us.'));
                        $('#info_state').removeClass('invisible');
                        $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
                    }
                    $('#button_add_blacklist').hide();
                    $('#button_remove_blacklist').show();
                    $('#unsubscribed_info').hide();
                }
            })
            .guardedCatch(function () {
                $('#subscription_info').html(_t('An error occured. Please try again later or contact us.'));
                $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
            });
    });

    $('#button_remove_blacklist').click(function (e) {
        e.preventDefault();

        ajax.jsonRpc('/mailing/blacklist/remove', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    $('#subscription_info').html(_t('You are not authorized to do this!'));
                    $('#info_state').removeClass('invisible');
                    $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-error').addClass('alert-warning');
                }
                else
                {
                    if (result) {
                        $('#subscription_info').html(_t("You have been successfully <strong>removed from our blacklist</strong>. "
                                + "You are now able to be contacted by our services."));
                                $('#info_state').removeClass('invisible');
                        $info_state.removeClass('alert-warning').removeClass('alert-info').removeClass('alert-error').addClass('alert-success');
                        toggle_opt_out_section(true);
                    }
                    else {
                        $('#subscription_info').html(_t('An error occured. Please try again later or contact us.'));
                        $('#info_state').removeClass('invisible');
                        $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
                    }
                    $('#button_add_blacklist').show();
                    $('#button_remove_blacklist').hide();
                    $('#unsubscribed_info').hide();
                }
            })
            .guardedCatch(function () {
                $('#subscription_info').html(_t('An error occured. Please try again later or contact us.'));
                $('#info_state').removeClass('invisible');
                $info_state.removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning').addClass('alert-error');
            });
    });
});

// prettier-ignore
function toggle_opt_out_section(value) {
    var result = !value;
    $("#div_opt_out").find('*').attr('disabled',result);
    $("#button_add_blacklist").attr('disabled', false);
    $("#button_remove_blacklist").attr('disabled', false);
    if (value) { $('[name="button_subscription"]').addClass('clickable');  }
    else { $('[name="button_subscription"]').removeClass('clickable'); }
}
