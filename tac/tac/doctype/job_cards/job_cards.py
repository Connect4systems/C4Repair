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
    def on_submit(self):
        self.create_sales_invoice()
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
        
    def create_sales_invoice(self):
        """
        يتم استدعاؤها عند اعتماد المستند.
        تقوم بإنشاء Sales Invoice مع الأصناف من الجدول الفرعي والصنف الخدمي
        """
        if not self.items and not self.technical_fees:
            return
        technical_fees = 0.00
        settings = get_settings()
        customer = "Repair"

        if not frappe.db.exists("Customer", customer):
            frappe.throw(_("Customer '{0}' is required. Please create it first.").format(customer))

        # جلب إعدادات الرسوم الفنية
        technical_fees_item = settings.technical_fees_item
        technical_fees = self.technical_fees

        # إنشاء فاتورة المبيعات
        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "due_date": frappe.utils.nowdate(),
            "job_cards": self.name,
            "custom_agent": self.agent,
            "custom_mobile": self.mobile,
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
            default_target_warehouse = frappe.db.get_single_value("TAC Settings", "default_target_warehouse")
            bom_item_meta = frappe.get_meta("BOM Item")

            diagram_field_candidates = [
                fieldname
                for fieldname in (
                    "daigram_number",
                    "custom_daigram_number",
                    "diagram_number",
                    "custom_diagram_number",
                )
                if bom_item_meta.has_field(fieldname)
            ]

            bom_item_fields = ["name", "idx", "item_code"] + diagram_field_candidates
            bom_item_rows = frappe.get_all(
                "BOM Item",
                filters={"parent": bom_doc.name},
                fields=bom_item_fields,
                order_by="idx asc"
            )
            bom_item_by_name = {d.get("name"): d for d in bom_item_rows}
            bom_item_by_idx = {d.get("idx"): d for d in bom_item_rows}

            items = []
            base_url = frappe.utils.get_url()  # جلب الدومين الأساسي للنظام

            for row in bom_doc.items:
                item_details = frappe.db.get_value(
                    "Item", row.item_code, ["item_name", "image"], as_dict=True
                )
                if not item_details:
                    item_details = {"item_name": row.item_code, "image": ""}
                
                latest_item_price = frappe.get_all(
                    "Item Price",
                    filters={"item_code": row.item_code, "price_list": price_list},
                    fields=["price_list_rate"],
                    order_by="modified desc",
                    limit=1
                )
                price = latest_item_price[0]["price_list_rate"] if latest_item_price else 0

                available_qty = 0
                if default_target_warehouse:
                    available_qty = frappe.db.sql(
                        """
                        SELECT COALESCE(SUM(actual_qty), 0)
                        FROM `tabBin`
                        WHERE item_code = %s AND warehouse = %s
                        """,
                        (row.item_code, default_target_warehouse)
                    )[0][0] or 0
                
                daigram_number = None
                bom_item_row = bom_item_by_name.get(row.name) or bom_item_by_idx.get(row.idx)

                for fieldname in diagram_field_candidates:
                    if bom_item_row:
                        daigram_number = bom_item_row.get(fieldname)
                    if daigram_number in (None, ""):
                        daigram_number = frappe.db.get_value(
                            "BOM Item",
                            {"parent": bom_doc.name, "idx": row.idx},
                            fieldname
                        )
                    if daigram_number in (None, ""):
                        daigram_number = getattr(row, fieldname, None)
                    if daigram_number not in (None, ""):
                        break

                if daigram_number in (None, ""):
                    daigram_number = 0
                image = item_details.get("image") or ""

                items.append({
                    "item_code": row.item_code,
                    "daigram_number":daigram_number,
                    "item_name": row.item_name or item_details["item_name"],
                    "price": price,
                    "qty": row.qty,
                    "available_qty": available_qty,
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
            default_bom = frappe.db.get_value(
                "BOM",
                {"item": item, "docstatus": 1, "is_active": 1, "is_default": 1},
                "name"
            )

            if default_bom:
                return default_bom

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