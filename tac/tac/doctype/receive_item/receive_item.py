import frappe
from frappe.model.document import Document

class ReceiveItem(Document):
	def on_submit(self):
		self.create_job_cards_base_on_receive_item()
	# def on_cancel(self):
	# 	item_caed = frappe.get_doc("Item Card", self.item_card)
	# 	item_caed.db_set("status","Received")
	# 	self.db_set("job_cards",None)
	# def before_cancel(self):
	# 	# إلغاء جميع Job Cards المرتبطة بهذا Receive Item
	# 	self.cancel_related_job_cards(self)

	# def cancel_related_job_cards(self):
	# 	# البحث عن جميع Job Cards المرتبطة بـ Receive Item الحالي
	# 	job_cards = frappe.get_all("Job Card", 
	# 		filters={"receive_item": self.name}, 
	# 		fields=["name", "docstatus"]
	# 	)

	# 	# إلغاء كل Job Card إذا كانت حالة التسليم 1 (Submitted)
	# 	for jc in job_cards:
	# 		if jc.docstatus == 1:
	# 			job_card = frappe.get_doc("Job Card", jc.name)
	# 			job_card.cancel()
	# 			frappe.db.commit()  # حفظ التغييرات فورًا
				
	# 	# إضافة تعليق للإشارة إلى الإلغاء
	# 	frappe.msgprint(_("تم إلغاء جميع Job Cards المرتبطة بهذا العنصر."))
	def create_job_cards_base_on_receive_item(self):
		if frappe.db.exists("Job Cards", {"receive_item":self.name}):
			return True
		else:
			new_receive_item = self.create_job_cards()
			self.db_set("job_cards_created", 1)
			self.db_set("job_cards", new_receive_item.name)
			item_caed = frappe.get_doc("Item Card", self.item_card)
			item_caed.db_set("status","To Deliver") 
			return new_receive_item

	def create_job_cards(self):
		new_doc = frappe.new_doc("Job Cards")
		new_doc.item_code = self.item_code
		new_doc.item_code_copy = self.item_code
		new_doc.item_name = self.item_name
		new_doc.image_url = self.image_url
		new_doc.customer_name = self.customer_name
		new_doc.customer_mobile = self.customer_mobile
		new_doc.serial_number = self.serial_number
		new_doc.warranty_status = self.warranty_status
		new_doc.warranty_expire_date = self.warranty_expire_date
		new_doc.register_date = self.register_date
		new_doc.item_card = self.item_card
		new_doc.receive_item = self.name
		new_doc.insert()

		return new_doc