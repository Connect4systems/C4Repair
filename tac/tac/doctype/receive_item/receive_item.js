// Copyright (c) 2025, Asofi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Receive Item", {
	refresh(frm) {
		if(frm.doc.docstatus==1)
        {
            frm.add_custom_button(__("Job Cards"), function() {
                frappe.set_route('Form', "Job Cards", frm.doc.job_cards);
            });
		}
	},
    item_code: function(frm) {
        if (frm.doc.item_code) {
            frappe.db.get_value("Item", frm.doc.item_code, "image").then(r => {
                if (r.message && r.message.image) {
                    // ضبط قيمة حقل الصورة في النموذج
                    frm.set_value("image_url", r.message.image);
                    frm.refresh_field("image_url");
                    // في بعض الأحيان تحتاج لعمل refresh للحقل
                    frm.refresh_field("image_url");
                } else {
                    // إذا لا توجد صورة في الصنف
                    frm.set_value("image_url", "");
                }
            });
        } else {
            frm.set_value("image_url", "");
        }
    },
    onload: function (frm) {
        // استخدام دالة غير متزامنة لجلب القيمة
        frappe.db.get_single_value('TAC Settings', 'default_target_warehouse')
            .then(defaultTargetWarehouse => {
                if (defaultTargetWarehouse) {
                    // التأكد من وجود المستودع قبل التعيين
                    frappe.db.exists('Warehouse', defaultTargetWarehouse)
                        .then(exists => {
                            if (exists) {
                                frm.set_value("target_warehouse", defaultTargetWarehouse);
                            } else {
                                frappe.msgprint({
                                    title: __("مستودع غير موجود"),
                                    indicator: "red",
                                    message: __("المستودع المحدد في الإعدادات غير موجود: {0}", [defaultTargetWarehouse])
                                });
                            }
                        });
                } else {
                    frappe.msgprint({
                        title: __("إعدادات ناقصة"),
                        indicator: "red",
                        message: __("يجب تعبئة حقل 'Default Target Warehouse' في إعدادات أولاً")
                    });
                }
            });                
    },
});
