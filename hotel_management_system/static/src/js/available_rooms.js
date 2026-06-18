/** @odoo-module **/
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import '@website_sale/js/website_sale';

var today = new Date();
var dd = String(today.getDate()).padStart(2, '0');
var mm = String(today.getMonth() + 1).padStart(2, '0');
var yyyy = today.getFullYear();
today = yyyy + '-' + mm + '-' + dd;

$(".wk_check_in").prop("min", today);

$('.wk_check_out').on('click', function () {
    if ($(".wk_check_in").val()) {
        var check_in_val = $(".wk_check_in").val();
        var currentCheckin = new Date(check_in_val);
        currentCheckin.setDate(currentCheckin.getDate() + 1);
        var formatted_checkoutDate = JSON.stringify(currentCheckin);
        $(this).prop("min", formatted_checkoutDate.slice(1, 11));
    }
});

$("#check_in_cart").prop("min", today);

$('#check_in_cart').on('change', function () {
    if (Date.parse($("#check_in_cart").val()) >= Date.parse($("#check_out_cart").val())) {
        $("#check_out_cart").val(null);
    }
});

$('#check_out_cart').on('click', function () {
    if ($("#check_in_cart").val()) {
        var check_in_val = $("#check_in_cart").val();
        var currentCheckin = new Date(check_in_val);
        currentCheckin.setDate(currentCheckin.getDate() + 1);
        var formatted_checkoutDate = JSON.stringify(currentCheckin);
        $(this).prop("min", formatted_checkoutDate.slice(1, 11));
    }
});

$(document).ready(function () {
    $('.add_Guest_span').on('click', function () {
        $('#addguestModalCenter').modal('show');
        var table_id = $(this).parent('div').parent('div').children('table').attr('id');
        $('.table_id_store').val(table_id);
    })
    
    $('.addGuestModal_button').on('click', function () {
        var fullName = $('.fullName').val();
        var genderValue = $("input[name='genderinlineRadioOptions']:checked").val();
        var age = $('.age').val();
        var table_id_store = $('.table_id_store').val();

        if (fullName && genderValue && table_id_store) {
            var desire_table = $('#accordionGuest').find("table#" + table_id_store);
            var tbody_val = desire_table.children('tbody');
            var tbody_div = tbody_val.first();

            var select_option = '';
            if (genderValue == "male") {
                select_option = `
                    <option value="male" selected>Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>`;
            } else if (genderValue == "female") {
                select_option = `
                    <option value="male">Male</option>
                    <option value="female" selected>Female</option>
                    <option value="other">Other</option>`;
            } else {
                select_option = `
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other" selected>Other</option>`;
            }

            tbody_div.append(`
                <tr>
                    <td>
                        <input class="form-control" type="text" name="name" value="${fullName}" required="true"/>
                    </td>
                    <td>
                        <select class="form-control" name="gender" id="gender" required="true">
                            ${select_option}
                        </select>
                    </td>
                    <td>
                        <input class="form-control" type="number" value="${age}" name="age" required="true"/>
                    </td>
                    <td>
                        <span type="button" class="btn mt-2 mb-2 btn-danger btn-sm inline remove_row">Remove</span>
                    </td>
                </tr>
            `);

            $('#addguestModalCenter').modal('hide');
        }
    });
    
    $('.guest_info_body').on('click', '.remove_row', function () {
        var tbody_val = $(this).parent('td').parent('tr').parent('tbody');
        if (tbody_val.children('tr').length > 1) {
            $(this).closest('tr').remove();
        }
    });

    $('#wk_check_in').on('change', function () {
        if (Date.parse($("#wk_check_in").val()) >= Date.parse($("#wk_check_out").val())) {
            $("#wk_check_out").val(null);
        }
    });

$('#submit_detail').on('click', function () {
    var info_dict = {};
    var check_point = 0;
    var errorMessageText = ""; 

    $('#dynamic-error-messages-container').empty();
    $("#dynamicExtraChargeMessage").remove();

    $('.outer_div').each(function () {
        let card = $(this).parents('.card-header');
        let requiredAdultsPerTable = 0;
        let requiredChildrenPerTable = 0;

        let adultGuestElement = card.find('#adult_guest');
        if (adultGuestElement) {
            requiredAdultsPerTable = parseInt(adultGuestElement.text().trim());
        }
        let childrenGuestElement = card.find('#children_guest');
        if (childrenGuestElement) {
            requiredChildrenPerTable = parseInt(childrenGuestElement.text().trim());
        }


        var productNameElement = card.find('.name_short_of_room');
        var productName = productNameElement.text().trim();
        if (productNameElement.length != 0){
        var line_id = $(this).attr('id');
        var data_list = [];

        var currentTableAdults = 0;
        var currentTableChildren = 0;

        var roomMaxAdult = parseInt($(this).find('.max_adult').val()) || 0;
        var roomMaxChild = parseInt($(this).find('.max_child').val()) || 0;

        $(this).children('table').children('tbody').find('tr').each(function (i, el) {
            var $tds = $(this).find("td");
            var dict = {};
            var hasMissingDataInRow = false;

            $tds.each(function (j, val) {
                let $child = $(this).children();
                let childType = $child.attr('type');
                let childName = $child.attr('name');
                let childVal = $child.val();

                if (childType === "number" && childName === "age") {
                    let age = parseInt(childVal);
                    if (isNaN(age) || age < 0) {
                        if (check_point === 0) {
                            check_point = 3;
                            errorMessageText = `Please fill correct age in ${productName} for booking.`;
                        }
                        hasMissingDataInRow = true;
                    } else if (age >= 18) {
                        currentTableAdults += 1;
                    } else {
                        currentTableChildren += 1;
                    }
                }

                if (!childVal && childType !== "button" && childName !== 'age') {
                    hasMissingDataInRow = true;
                } else if (childName === 'age' && (childVal === "" || isNaN(parseInt(childVal)))) {
                    hasMissingDataInRow = true;
                }

                if (childType !== "button") {
                    dict[childName] = childVal;
                }
            });

            if (hasMissingDataInRow && check_point < 1) { 
                check_point = 1;
                errorMessageText = `Please fill data in all fields for ${productName}.`;
            }
            data_list.push(dict);
        
        });

        // if (currentTableAdults > roomMaxAdult || currentTableChildren > roomMaxChild) {
        //     if (check_point < 2) {
        //         check_point = 2;
        //         errorMessageText = `Please manage child and adult according room requirement in ${productName}.`;
        //     }
        // }

        if (check_point === 0 && (currentTableAdults !== requiredAdultsPerTable || currentTableChildren !== requiredChildrenPerTable)) {
            check_point = 4;
            errorMessageText = `You need to add ${requiredAdultsPerTable} adults and ${requiredChildrenPerTable} children, in ${productName}.`;
        }

        info_dict[line_id] = data_list;
    }
    });
    if (check_point !== 0) {
        if (errorMessageText) {
            const warningP = $('<p>').addClass('alert alert-warning m-4').text(errorMessageText);
            $('#dynamic-error-messages-container').append(warningP);
        }
    } else { 
        rpc('/guest/info', { guest_detail: info_dict }).then(function (val) {
            window.location = '/shop/checkout?express=1';
        });
    }
});

    $('#wk_adult, #wk_child').on('input', updateTotalMembers);
});

$('.emptyCart').on('click', function () {
    rpc('/empty/cart').then(function () {
        $('#modalAbandonedCart').modal('hide');
    });
});

$(document).on('click', '#check_booking_room_availability', function () {
    if ($('#check_in_cart').val() && $('#check_out_cart').val()) {
        $("#caution_date").css("display", "none");
        var hotel_id = $('#prod_hotel_id').val();
        var check_in = $('#check_in_cart').val();
        var check_out = $('#check_out_cart').val();
        var product_template_id = $('input[name="product_template_id"]').val();
        var product_id = $('input[name="product_id"]').val();
        var des_att_value = $(".no_variant:checked").attr('data-attribute_name');
        var des_value = $(".no_variant:checked").attr('data-value_name');
        var requirement_qty = $('input[name="add_qty"]').val() || 1;
        var value = '';

        const adult = parseInt($('#wk_adult').val()) || 0;
        const child = parseInt($('#wk_child').val()) || 0

        if (des_att_value && des_value) {
            value = des_att_value + ":" + des_value
        }
        rpc('/available/qty/details', {
            hotel_id: hotel_id,
            check_in: check_in,
            check_out: check_out,
            product_template_id: product_template_id,
            product_id: product_id,
            requirement_qty: requirement_qty,
            availabilty_check: '0',
            order_des: value,
            adult: adult,
            child: child,
        }).then(function (val) {

            if (val['result'] == 'fail') {
                if (val['msg'] == ' ') {
                    $(".msg_alert").css("display", "none");
                    $("#caution_msg").css("display", "block");
                }
                else {
                    $(".msg_alert").css("display", "none");
                    $("#caution_msg").css("display", "block");
                    $("#caution_msg").text(val['msg']);
                }
            }
            else if (val['result'] == 'unmatched') {
                $('#modalAbandonedCart').find('.warn-msg').text(val['msg']);
                if (val['both']) $('.warn-rm-msg').show();
                else $('.warn-rm-msg').hide();
                $('#modalAbandonedCart').modal('show');
            }
            else {
                // $("#available_room").css("display", "none");
                $(".msg_alert").css("display", "none");
                $("#success_msg").css("display", "block");
                setTimeout(function () { window.location = '/shop/cart'; }, 1000);
            }
        });
    }
    else {
        $(".msg_alert").css("display", "none");
        $("#caution_date").css("display", "block");
    }
});

publicWidget.registry.WebsiteSale.include({
    events: Object.assign(publicWidget.registry.WebsiteSale.prototype.events, {
        'change #check_in_cart': '_onchangecheck_in_out_cart',
        'change #check_out_cart': '_onchangecheck_in_out_cart',
    }),
    _onchangecheck_in_out_cart: function () {
        $("input[name='add_qty']").trigger('change');
    },
    _getOptionalCombinationInfoParam: function () {
        var self = this;
        var check_in = self.$el.find('#check_in_cart').val();
        var check_out = self.$el.find('#check_out_cart').val();
        if (check_in && check_out) {
            const check_in_date = new Date(check_in);
            const check_out_date = new Date(check_out);
            const diff_time = Math.abs(check_out_date - check_in_date);
            const days = Math.ceil(diff_time / (1000 * 60 * 60 * 24));
            return {
                days_count: days
            };
        }
    },
    _getCombinationInfo: function (ev) {
        if ($(ev.target).hasClass('variant_custom_value')) {
            return Promise.resolve();
        }

        const $parent = $(ev.target).closest('.js_product');
        if(!$parent.length){
            return Promise.resolve();
        }
        const combination = this.getSelectedVariantValues($parent);

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt($parent.find('.product_template_id').val()),
            'product_id': this._getProductId($parent),
            'combination': combination,
            'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
            'parent_combination': [],
            'context': this.context,
            ...this._getOptionalCombinationInfoParam($parent),
        }).then((combinationData) => {
            if(combinationData?.is_room){
                $parent.find('.o_we_buy_now').hide();
            }
            if (this._shouldIgnoreRpcResult()) {
                return;
            }
            this._onChangeCombination(ev, $parent, combinationData);
            this._checkExclusions($parent, combination, combinationData.parent_exclusions);
        });
    },
});

document.querySelectorAll(".hotel-menu a").forEach(anchor => {
    anchor.addEventListener("click", function (e) {
        e.preventDefault();

        document.querySelectorAll(".hotel-menu a").forEach(link => {
            link.classList.remove("active-underline");
        });

        // Add underline to the clicked link
        this.classList.add("active-underline");

        const targetId = this.getAttribute("href").substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 50,
                behavior: "smooth"
            });
        }
    });
});

function updateTotalMembers() {
    let adults = parseInt($('#wk_adult').val()) || 0;
    let children = parseInt($('#wk_child').val()) || 0;

    let maxAdultCountElement = document.getElementById('max_adult_count');
    let maxAdultValue;
    if (maxAdultCountElement) {
        maxAdultValue = parseInt(maxAdultCountElement.textContent.trim());
    }

    let maxChildren = document.getElementById('max_child_count');
    let maxChildrenValue;
    if(maxChildren){
        maxChildrenValue = parseInt(maxChildren.textContent.trim());
    }

    if(adults > maxAdultValue){
        $('#wk_adult').val(maxAdultValue);
        adults = maxAdultValue;
    }
    if(children > maxChildrenValue){
        $('#wk_child').val(maxChildrenValue);
        children = maxChildrenValue;
    }

    let total = adults + children;
    $('#total-members-text').text(total + " member" + (total !== 1 ? "s" : ""));

    let baseGuest = document.getElementById('baseoccupancyId');
    let baseGuestValue;
    if(baseGuest){
        baseGuestValue = parseInt(baseGuest.textContent.trim());
    }

    const existingDynamicMessageDiv = document.getElementById('dynamicExtraChargeMessage');
    if (existingDynamicMessageDiv) {
        existingDynamicMessageDiv.remove();
    }

    if (total > baseGuestValue){
        const extraChargeElement = document.getElementById('extraChargeId');
        let currencySymbol = '';
        let extraChargeAmount = 0.0;

        if (extraChargeElement) {
            const textContent = extraChargeElement.textContent.trim();
            const match = textContent.match(/^(.*?)\s*(\d+(?:\.\d+)?)(?:\s*\/person)?$/);
            if (match) {
                currencySymbol = match[1] ? match[1].trim() : '';
                extraChargeAmount = parseFloat(match[2]);
            }
        }
        
        let calculatedExtraCharge = extraChargeAmount * (total - baseGuestValue);

        const extraChargeRefDiv = document.getElementById('extrachargeId');
        if (extraChargeRefDiv) {
            const newDiv = document.createElement('div');
            newDiv.id = 'dynamicExtraChargeMessage';
            const dynamicString = "Extra Charge : +" + currencySymbol + calculatedExtraCharge.toFixed(2) + '/night';
            newDiv.textContent = dynamicString;
            newDiv.classList.add('mt-2', 'text-success', 'fw-bold');
            if(calculatedExtraCharge.toFixed(2) > 0){
                extraChargeRefDiv.insertAdjacentElement('afterend', newDiv);
            }
        } else {
            console.warn("Element with ID 'extrachargeId' not found. Cannot append new div.");
        }
    }
}

$(document).ready(function() {
    $('#wk_adult, #wk_child').on('input', updateTotalMembers);
    updateTotalMembers();
});
