import frappe
from frappe.model.document import Document

class ReceiveItem(Document):
	def on_submit(self):
		self.set_status_if_available("Received")
		self.create_job_cards_base_on_receive_item()

	def set_pickup_status(self):
		self.set_status_if_available("Pickup")

	@frappe.whitelist()
	def mark_as_returned(self):
		if self.docstatus != 1:
			frappe.throw("Return is allowed only for submitted Receive Item.")

		if self.status == "Returned":
			return

		self.set_status_if_available("Returned")

	def set_status_if_available(self, status_value):
		try:
			self.db_set("status", status_value, update_modified=False)
			self.status = status_value
		except Exception as exc:
			if "Unknown column 'status'" in str(exc):
				return
			raise

	def before_cancel(self):
		self.cancel_related_documents()

	def on_cancel(self):
		self.clear_connection_fields()

	def cancel_related_documents(self):
		job_cards = frappe.get_all(
			"Job Cards",
			filters={"receive_item": self.name},
			fields=["name", "docstatus", "sales_invoice"],
		)

		for jc in job_cards:
			sales_invoice_name = jc.get("sales_invoice")
			if sales_invoice_name and frappe.db.exists("Sales Invoice", sales_invoice_name):
				sales_invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
				if sales_invoice_doc.docstatus == 1:
					sales_invoice_doc.flags.ignore_permissions = True
					sales_invoice_doc.cancel()

			if jc.docstatus == 1:
				job_card_doc = frappe.get_doc("Job Cards", jc.name)
				job_card_doc.flags.ignore_permissions = True
				job_card_doc.cancel()

	def clear_connection_fields(self):
		meta = frappe.get_meta("Receive Item")
		if meta.has_field("job_cards"):
			frappe.db.set_value("Receive Item", self.name, "job_cards", None, update_modified=False)

		job_cards = frappe.get_all(
			"Job Cards",
			filters={"receive_item": self.name},
			fields=["name", "sales_invoice"],
		)

		for jc in job_cards:
			jc_meta = frappe.get_meta("Job Cards")
			if jc_meta.has_field("receive_item"):
				frappe.db.set_value("Job Cards", jc.name, "receive_item", None, update_modified=False)
			if jc_meta.has_field("sales_invoice"):
				frappe.db.set_value("Job Cards", jc.name, "sales_invoice", None, update_modified=False)

			sales_invoice_name = jc.get("sales_invoice")
			if sales_invoice_name and frappe.db.exists("Sales Invoice", sales_invoice_name):
				si_meta = frappe.get_meta("Sales Invoice")
				if si_meta.has_field("job_cards"):
					frappe.db.set_value("Sales Invoice", sales_invoice_name, "job_cards", None, update_modified=False)
				if si_meta.has_field("custom_receive_item"):
					frappe.db.set_value("Sales Invoice", sales_invoice_name, "custom_receive_item", None, update_modified=False)

	def create_job_cards_base_on_receive_item(self):
		if frappe.db.exists("Job Cards", {"receive_item":self.name}):
			return True
		else:
			new_receive_item = self.create_job_cards()
			self.db_set("job_cards_created", 1)
			self.db_set("job_cards", new_receive_item.name)
			return new_receive_item

	def create_job_cards(self):
		new_doc = frappe.new_doc("Job Cards")
		new_doc.item_code = self.item_code
		new_doc.item_code_copy = self.item_code
		new_doc.item_name = self.item_name
		new_doc.image_url = self.image_url
		if new_doc.meta.has_field("customer_name"):
			new_doc.customer_name = getattr(self, "customer_name", None) or getattr(self, "agent", None)
		if new_doc.meta.has_field("customer_mobile"):
			new_doc.customer_mobile = getattr(self, "customer_mobile", None) or getattr(self, "mobile", None)
		if new_doc.meta.has_field("agent"):
			new_doc.agent = getattr(self, "agent", None) or getattr(self, "customer_name", None)
		if new_doc.meta.has_field("mobile"):
			new_doc.mobile = getattr(self, "mobile", None) or getattr(self, "customer_mobile", None)
		new_doc.serial_number = self.serial_number
		new_doc.warranty_status = self.warranty_status
		new_doc.warranty_expire_date = self.warranty_expire_date
		new_doc.register_date = self.register_date
		new_doc.receive_item = self.name
		new_doc.insert()

		return new_doc