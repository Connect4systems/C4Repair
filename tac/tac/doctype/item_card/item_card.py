# Copyright (c) 2025, Asofi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr


class ItemCard(Document):
	@frappe.whitelist()
	def create_receive_item_base_on_item_card(self):
		# if frappe.db.exists("Receive Item", {"item_card":self.name}):
		# 	return True
		# else:
		new_receive_item = self.create_receive_item()
		self.db_set("receive_item_created", 1)
		self.db_set("receive_item", new_receive_item.name)
		self.db_set("status", "Received")
		
		return new_receive_item

	def create_receive_item(self):
		new_doc = frappe.new_doc("Receive Item")
		new_doc.item_code = self.item_code
		new_doc.item_name = self.item_name
		# new_doc.item_image = self.item_image
		new_doc.customer_name = self.customer_name
		new_doc.customer_mobile = self.customer_mobile
		new_doc.serial_number = self.serial_number
		new_doc.warranty_status = self.warranty_status
		new_doc.warranty_expire_date = self.warranty_expire_date
		new_doc.register_date = self.register_date
		new_doc.item_card = self.name
		new_doc.insert()
		
		return new_doc


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_serial_numbers(doctype, txt, searchfield, start, page_len, filters):
    """
    Returns a list of 'Serial No' that are not yet used in any 'Item Card'.
    This function is designed to be used as a query for a Link field.
    """
    
    used_serials = frappe.get_all(
        "Item Card",
        filters={"docstatus": ["!=", 2], "serial_number": ["is", "set"]},
        pluck="serial_number"
    )
    
    serial_no_filters = [
        ["name", "not in", used_serials or ['']]
    ]
    
    if txt:
        serial_no_filters.append(["name", "like", f"%{cstr(txt)}%"])
        
    available_serials = frappe.get_list(
        "Serial No",
        fields=["name", "item_code"],
        filters=serial_no_filters,
        start=start,
        page_length=page_len,
        order_by="name"
    )
	# Format the results to return a list of lists with serial name and item code
    formatted_results = []
    for serial in available_serials:
        formatted_results.append([serial.name, serial.item_code])
        
    return formatted_results