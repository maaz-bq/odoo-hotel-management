# -*- coding: utf-8 -*-
##########################################################################
# Author : Webkul Software Pvt. Ltd. (<https://webkul.com/>;)
# Copyright(c): 2017-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>;
##########################################################################
import mimetypes

from odoo import fields, models, _, api
import logging
_logger = logging.getLogger(__name__)

FILE_TYPE = {
    "PDF": ["application/pdf"],
    "Image": ["image/png", "image/jpeg", "image/jpg", "image/jpeg", "image/bmp", "image/tiff", "image/webp", "image/gif", "image/avif"],
}


class AttachDoc(models.TransientModel):
    _name = "customer.document"
    _description = "Attached customer document image"

    add_docs_ids = fields.One2many(
        "customer.document.lines", "doc_id", string="Attach Documents"
    )
    booking_id = fields.Many2one("hotel.booking")
    warning = fields.Char(compute="_check_file_type", default=None)

    def confirm_doc(self):
        """Confirm document wizard"""
        active_booking_id = self.env["hotel.booking"].browse(
            self._context.get("active_ids")
        )
        data = [[0, 0, {"file": doc.file, "name": doc.req_document_id.name}]
                for doc in self.add_docs_ids]
        template_id = self.env.ref(
            "hotel_management_system.hotel_booking_allot_id"
        )
        active_booking_id.write({"docs_ids": data, "status_bar": "allot"})

        active_booking_id.expected_check_out = active_booking_id.check_out
        
        allot_config = self.env["ir.config_parameter"].sudo(
        ).get_param("hotel_management_system.send_on_allot")
        if allot_config:
            template_id.send_mail(active_booking_id.id, force_send=True)

    @api.depends('add_docs_ids')
    def _check_file_type(self):
        for record in self:
            record.warning = ""

            if not record.add_docs_ids:
                record.warning = "Please upload at least one required document."
                continue
            for rec_doc in record.add_docs_ids:
                if not rec_doc.file:

                    # record.warning = f"Please upload your '{rec_doc.req_document_id.name if rec_doc.req_document_id else 'a document entry'}'."
                    record.warning = f"'{rec_doc.req_document_id.name if rec_doc.req_document_id else 'Document entry'}' \
                        cannot be left blank. Upload a valid {rec_doc.req_document_id.name if rec_doc.req_document_id else 'Document entry'}\
                        document."
                    break

                if rec_doc.file and rec_doc.req_document_id and rec_doc.req_document_id.document_type_ids:
                    allowed_mimetypes_for_this_doc = set()
                    allowed_type_names = []

                    for doc_type in rec_doc.req_document_id.document_type_ids:
                        doc_type_name = doc_type.name
                        allowed_type_names.append(doc_type_name)

                        mimetypes_from_config = FILE_TYPE.get(doc_type_name)
                        if mimetypes_from_config:
                            allowed_mimetypes_for_this_doc.update(
                                mimetypes_from_config)

                    if not allowed_mimetypes_for_this_doc:
                        record.warning = f"Document type(s) selected for '{rec_doc.file_name}' are not configured in allowed file types."
                        break

                    mimetype = mimetypes.guess_type(rec_doc.file_name)[0]

                    if mimetype is None or mimetype not in allowed_mimetypes_for_this_doc:
                        allowed_types_str = ", ".join(
                            sorted(allowed_type_names))
                        custom_warning = "a Pdf" if mimetype != "application/pdf" else "an Image"
                        record.warning = f"Only {allowed_types_str} files are allowed. The file '{rec_doc.file_name}' is not {custom_warning}."
                        break


class AttachDocLines(models.TransientModel):
    _name = "customer.document.lines"
    _description = "Attached customer document lines"

    name = fields.Char("Name")
    file = fields.Binary("File", required=True)
    file_name = fields.Char("File Name")
    doc_id = fields.Many2one("customer.document")
    req_document_id = fields.Many2one(
        "hotel.booking.documents", string="Required documents")
