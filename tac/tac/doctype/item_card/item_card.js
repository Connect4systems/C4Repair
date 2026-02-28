// Copyright (c) 2025, Asofi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Card", {
	refresh: function(frm) {
        // This filter should only be applied when creating a NEW Item Card.
        // For existing cards, we want to see the selected serial number without filtering it out.
        if (frm.is_new()) {
            frm.set_query('serial_number', function() {
                return {
                    query: 'tac.tac.doctype.item_card.item_card.get_available_serial_numbers'
                };
            });
        }		
		if(frm.doc.docstatus==1){
			// if (! frm.doc.receive_item){
				frm.add_custom_button(__("Create Receive Item"), function() {
					if (frm.is_dirty()){
						frappe.throw(__("You have unsaved changes in this form. Please save before you continue."));
					}
					frappe.call({
						doc: frm.doc,
						method: "create_receive_item_base_on_item_card",
							callback: function(r) {
								if(! r.exc){
									frappe.show_alert({message:__("Receive item created successfully"), indicator:'green'});
									frappe.set_route('Form', "Receive Item", frm.doc.receive_item);
								}
								if(r.message==true){
									frappe.set_route('Form', "Receive Item", frm.doc.receive_item);
								}
								frm.reload_doc();
							}
						});
					});
			// }
			// else {
			// 	frm.add_custom_button(__("Receive Item"), function() {
			// 		frappe.set_route('Form', "Receive Item", frm.doc.receive_item);
			// 	});
			// }
		}

	},
    // Optional: If you change the item code, you might want to clear the serial number
    item_code: function(frm) {
        if(frm.doc.serial_number) {
            frm.set_value('serial_number', '');
        }
    }	
});;
