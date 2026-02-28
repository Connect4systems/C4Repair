cur_frm.cscript.onload = function () {
	cur_frm.set_query("item_code", function () {
		return erpnext.queries.item({ is_stock_item: 1 });
	});
};
// has_serial_no: 1