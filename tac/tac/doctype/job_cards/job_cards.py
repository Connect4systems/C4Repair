# Copyright (c) 2025, Asofi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
class JobCards(Document):
    def validate(self):
        self.validate_for_items()
    def before_save(self):
        # self.calculate_total_spare_parts_amount()
        pass
    # def on_cancel(self):
    #     item_caed = frappe.get_doc("Item Card", self.item_card)
    #     item_caed.db_set("status","To Deliver")        
    #     self.db_set("receive_item",None)
    def on_submit(self):
        self.create_sales_invoice()
        self.create_stock_entry()
    def validate_for_items(self):
        for d in self.get("items"):
            tot_avail_qty = frappe.db.sql(
                "select projected_qty from `tabBin` \
                where item_code = %s ",
                (d.item_code),
            )
            d.available_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0
    def calculate_total_spare_parts_amount(self):
        total_amount = 0
        for item in self.items:
            price = float(item.price) 
            qty = float(item.qty)
            total_amount += price * qty
        self.total_spare_parts_amount = total_amount
        self.total_amount = self.total_spare_parts_amount + self.technical_fees
        
    def create_stock_entry(self):
        """
        يتم استدعاؤها عند اعتماد المستند.
        تقوم بإنشاء Stock Entry.
        """
        settings = get_settings()
        target_warehouse = settings.default_target_warehouse
        source_warehouse = settings.default_source_warehouse       
        # إنشاء Stock Entry
        new_doc = frappe.get_doc({
            'doctype': 'Stock Entry',
            'transaction_date': self.receiving_date,
            'stock_entry_type': 'Material Transfer',
            'customer': self.customer_name,
            'from_warehouse': target_warehouse,
            'to_warehouse': source_warehouse ,
            'item_card': self.item_card,
            'job_cards': self.name
        })
        
        new = new_doc.append("items", {})
        new.item_code = self.item_code
        new.item_name = self.item_name
        new.qty = 1
        new.customer = self.customer_name
        new.custom_serial_on = self.serial_number
        new_doc.insert(ignore_permissions=True)
        new_doc.submit()
        self.db_set("stock_entry", new_doc.name)
        frappe.msgprint(_("تم إنشاء  إدخال المخزون: {0}").format(
            frappe.utils.get_link_to_form("Stock Entry", new_doc.name)
        )) 
        
    def create_sales_invoice(self):
        """
        يتم استدعاؤها عند اعتماد المستند.
        تقوم بإنشاء Sales Invoice مع الأصناف من الجدول الفرعي والصنف الخدمي
        """
        if not self.items and not self.technical_fees:
            return
        technical_fees = 0.00
        settings = get_settings()
        
        if not self.customer_name:
            frappe.throw(_("الرجاء تحديد عميل قبل الإرسال"))

        # جلب إعدادات الرسوم الفنية
        technical_fees_item = settings.technical_fees_item
        technical_fees = self.technical_fees

        # إنشاء فاتورة المبيعات
        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer_name,
            "due_date": frappe.utils.nowdate(),
            "job_cards": self.name,
            "item_card": self.item_card,
            "items": []
        })

        # إضافة أصناف الجدول الفرعي
        if self.items:
            for item_row in self.items:
                sales_invoice.append("items", {
                    "item_code": item_row.item_code,
                    "qty": item_row.qty,
                    "rate": item_row.price
                })
        # إضافة الصنف الخدمي إذا كانت القيم موجودة
        if not self.technical_fees:
            technical_fees = 0.00
        if technical_fees_item:
            sales_invoice.append("items", {
                "item_code": technical_fees_item,
                "qty": 1,
                "rate": technical_fees,
                "description": "رسوم فنية"
            })
        else:
            frappe.throw("الصنف الخدمي غير محدد في الاعدادات")      
        # حفظ الفاتورة وإرسالها
        sales_invoice.insert(ignore_permissions=True)
        sales_invoice.submit()

        # ربط الفاتورة مع Job Card
        self.db_set("sales_invoice", sales_invoice.name)
        frappe.msgprint(_("تم إنشاء فاتورة مبيعات: {0}").format(
            frappe.utils.get_link_to_form("Sales Invoice", sales_invoice.name)
        ))   
    
    @frappe.whitelist()
    def get_items_from_bom(bom):
        if not bom:
            return []

        try:
            bom_doc = frappe.get_doc("BOM", bom)
            price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

            items = []
            base_url = frappe.utils.get_url()  # جلب الدومين الأساسي للنظام

            for row in bom_doc.items:
                item_details = frappe.db.get_value(
                    "Item", row.item_code, ["item_name", "image"], as_dict=True
                )
                if not item_details:
                    item_details = {"item_name": row.item_code, "image": ""}
                
                # جلب سعر الصنف من Item Price
                price = frappe.db.get_value(
                    "Item Price",
                    {"item_code": row.item_code, "price_list": price_list},
                    "price_list_rate"
                ) or 0  # إذا لم يتم العثور على سعر، يكون 0
                
                daigram_number = frappe.db.get_value(
                    "BOM Item",
                    {"item_code": row.item_code},
                    "daigram_number"
                ) or ""
                # ضبط رابط الصورة ليكون صالحًا للعرض
                image = f"{base_url}/{item_details.get('image')}" if item_details.get("image") else "https://via.placeholder.com/50"

                items.append({
                    "item_code": row.item_code,
                    "daigram_number":daigram_number,
                    "item_name": item_details["item_name"],
                    "price": price,
                    "qty": row.qty,
                    "available_qty": "",
                    "image": image
                })
            return items
        except Exception as e:
            frappe.log_error(f"Error fetching items from BOM '{bom}': {str(e)}", "get_items_from_bom")
            return []
    @frappe.whitelist()
    def get_bom(self, item):
        """
        من الصنف (item_code) يتم استدعاؤها للحصول على الـ BOM المرتبطة والمعتمدة.
        """
        if not item:
            return ""
        
        try:
            bom_list = frappe.get_all(
                "BOM",
                filters={"item": item, "docstatus": 1, "is_active": 1},
                fields=["name"],
                limit=1
            )
            if bom_list:
                return bom_list[0]["name"]
            else:
                return ""
        except Exception as e:
            frappe.log_error(_("Error fetching BOM for item '{0}': {1}").format(item, str(e)), "get_bom")
            return ""
    @frappe.whitelist()
    def get_available_qty(self,item_code):
        tot_avail_qty = frappe.db.sql(
            "select projected_qty from `tabBin` \
            where item_code = %s ",
            (item_code),
        )
        available_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0
        return  available_qty        
def get_settings():
    """Fetches the TAC Setting."""
    # Fetch the latest settings
    settings = frappe.get_single("TAC Settings")
    return settings 

@frappe.whitelist()
def get_item_availability(item_code, warehouse):
    # **هذه الدالة تحتاج إلى تعديل لتناسب نظام المخزون الخاص بك**
    # **يجب أن تستعلم عن الكمية المتوفرة في المخزن المحدد**
    # **مثال:**
    # item = frappe.get_doc("Item", item_code)
    # available_qty = item.get_qty_in_warehouse(warehouse) #هذه الدالة غير موجودة ويجب عليك تعديلها
    # return {"available_qty": available_qty}
    # **بديل باستخدام SQL (مثال):**
    available_qty = frappe.db.sql("""
        SELECT SUM(actual_qty)
        FROM `tabBin`
        WHERE item_code = %s AND warehouse = %s
    """, (item_code, warehouse))[0][0]

    if available_qty is None:
        available_qty = 0

    return {"available_qty": available_qty}