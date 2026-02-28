let sparePartsRequestId = 0;
const BOM_DEBUG = true;

frappe.ui.form.on("Job Cards", {
    setup: function(frm) {
        setBomQuery(frm);
    },
    refresh: function(frm) {
        addCSS();
        setBomQuery(frm);
        syncDefaultBomAndBuild(frm);
        // frm.set_df_property("technician_name", "hidden", 1);
        // frm.set_df_property("item_code", "hidden", 1);
    // //   setTimeout(() => {
    // //       const paymentEntryButton = document.querySelector('.document-link[data-doctype="Payment Entry"] .btn-new');
    // //       if (paymentEntryButton) {
    // //           paymentEntryButton.style.display = 'none';
    // //         }
    // //     }, 500);     
        setTimeout(() => {
            const salesInvoiceButton = document.querySelector('.document-link[data-doctype="Sales Invoice"] .btn-new');
            if (salesInvoiceButton) {
                salesInvoiceButton.style.display = 'none';
            }
        }, 500);
    },
    onload: function (frm) {
        setBomQuery(frm);
        syncDefaultBomAndBuild(frm);
        // استخدام دالة غير متزامنة لجلب القيمة
        // frappe.db.get_single_value('TAC Settings', 'default_target_warehouse')
        //     .then(defaultTargetWarehouse => {
        //         if (defaultTargetWarehouse) {
        //             // التأكد من وجود المستودع قبل التعيين
        //             frappe.db.exists('Warehouse', defaultTargetWarehouse)
        //                 .then(exists => {
        //                     if (exists) {
        //                         frm.set_value("target_warehouse", defaultTargetWarehouse);
        //                     } else {
        //                         frappe.msgprint({
        //                             title: __("مستودع غير موجود"),
        //                             indicator: "red",
        //                             message: __("المستودع المحدد في الإعدادات غير موجود: {0}", [defaultTargetWarehouse])
        //                         });
        //                     }
        //                 });
        //         } else {
        //             frappe.msgprint({
        //                 title: __("إعدادات ناقصة"),
        //                 indicator: "red",
        //                 message: __("يجب تعبئة حقل 'Default Target Warehouse' في إعدادات التأجير أولاً")
        //             });
        //         }
        //     });                
    },
    item_code: function(frm) {
        addCSS();
        setBomQuery(frm);
        frm.set_value("bom", null);
        syncDefaultBomAndBuild(frm);
    },
    bom: function(frm) {
        if (BOM_DEBUG) {
            console.debug("[Job Cards] BOM changed", {
                job_card: frm.doc.name,
                item_code: frm.doc.item_code,
                bom: frm.doc.bom
            });
        }
        buildTechnicalTab(frm);
    }
});

function setBomQuery(frm) {
    frm.set_query("bom", function() {
        const filters = {
            docstatus: 1,
            is_active: 1
        };

        if (frm.doc.item_code) {
            filters.item = frm.doc.item_code;
        }

        return {
            filters: filters
        };
    });
}

function syncDefaultBomAndBuild(frm) {
    if (!frm.doc.item_code) {
        buildTechnicalTab(frm);
        return;
    }

    if (frm.doc.bom) {
        frm.trigger("bom");
        return;
    }

    frappe.call({
        doc: frm.doc,
        method: "get_bom",
        args: {
            item: frm.doc.item_code
        },
        callback: function(r) {
            const defaultBom = r.message;
            if (defaultBom && defaultBom !== frm.doc.bom) {
                frm.set_value("bom", defaultBom).then(() => frm.trigger("bom"));
            } else {
                buildTechnicalTab(frm);
            }
        }
    });
}

function addCSS() {
    let css = `
        .spare-parts-table {
            width: 100% !important;
            border-collapse: collapse;
            font-family: sans-serif;
        }

        .spare-parts-table thead {
            display: table;
            width: 100%;
            background-color: #f1f1f1;
            position: sticky;
            top: 0;
        }

        .spare-parts-table tbody {
            display: block;
            max-height: calc(4 * 88px); /* ارتفاع 4 صفوف */
            overflow-y: auto;
        }

        .spare-parts-table tr {
            display: table;
            width: 100%;
            table-layout: fixed;
            height: 45px; /* ارتفاع كل صف */
        }

        .spare-parts-table th,
        .spare-parts-table td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: center;
            width: 20% !important;
        }

        .spare-parts-table tbody::-webkit-scrollbar {
            width: 6px;
        }

        .spare-parts-table tbody::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }

        .job-card-tabs { margin-bottom: 20px; }
        .job-card-details-section { 
            background-color: #fdf6ed;
            padding: 15px;
            border: 1px solid #ddd;
        }
        .spare-parts-table img {
            width: 80px;
            height: 60px;
            object-fit: cover;
            cursor: pointer;
        }
        .tab-bar {
            display: flex;
            border-bottom: 1px solid #ccc;
            background-color: #f8f8f8;
        }
    `;

    let style = document.createElement('style');
    style.innerHTML = css;
    document.head.appendChild(style);
}

function buildTechnicalTab(frm) {
    let item_code = frm.doc.item_code;
    let bom = frm.doc.bom;
    const requestId = ++sparePartsRequestId;

    if (BOM_DEBUG) {
        console.debug("[Job Cards] buildTechnicalTab", {
            requestId,
            job_card: frm.doc.name,
            item_code,
            bom
        });
    }

    if (!bom) {
        let html = getStaticLayout(frm, {
            technician_name: frm.doc.technician_name || "",
            item_code: frm.doc.item_code || "",
            items: [],
            no_bom_message: "No BOM found for this item.",
            image_url: frm.doc.image_url
        });
        frm.get_field("spare_parts").$wrapper.html(html);
        return;
    }

    frappe.call({
        doc: frm.doc,
        method: "get_items_from_bom",
        args: {
            bom: bom
        },
        callback: function(r2) {
            if (BOM_DEBUG) {
                console.debug("[Job Cards] get_items_from_bom response", {
                    requestId,
                    currentRequestId: sparePartsRequestId,
                    requestedBom: bom,
                    activeBom: frm.doc.bom,
                    hasException: Boolean(r2 && r2.exc),
                    rows: Array.isArray(r2 && r2.message) ? r2.message.length : 0,
                    message: r2 ? r2.message : null
                });
            }

            if (r2 && r2.exc) {
                frappe.msgprint({
                    title: __("BOM Fetch Error"),
                    indicator: "red",
                    message: __("Failed to load spare parts from BOM. Check console for details.")
                });
                return;
            }

            if (requestId !== sparePartsRequestId || bom !== frm.doc.bom) {
                if (BOM_DEBUG) {
                    console.debug("[Job Cards] stale response ignored", {
                        requestId,
                        currentRequestId: sparePartsRequestId,
                        requestedBom: bom,
                        activeBom: frm.doc.bom
                    });
                }
                return;
            }

            let items = r2.message || [];
            if (BOM_DEBUG && (!Array.isArray(items) || !items.length)) {
                console.warn("[Job Cards] no BOM items returned", {
                    bom,
                    item_code,
                    response: r2
                });
            }

            let html = getStaticLayout(frm, {
                technician_name: frm.doc.technician_name || "",
                item_code: frm.doc.item_code || "",
                items: items,
                image_url: frm.doc.image_url
            });

            frm.get_field("spare_parts").$wrapper.html(html);

            setTimeout(() => {
                addClickEventsToImages(frm);
                addDiagramSearch(frm);
                const table = frm.get_field("spare_parts").$wrapper.find(".spare-parts-table");
                if (table.length) {
                    table.css({
                        "max-height": "400px",
                        "overflow-y": "auto",
                        "overflow-x": "auto"
                    });
                }
            }, 300);
        }
    });
}

function getStaticLayout(frm, data) {
    let rowsHtml = buildTableRows(data.items);
    const leftImage = data.image_url;

    let html = `
      <div style="font-family: Arial, sans-serif; ">
        <div style="display: flex; border: 1px solid #ccc;">
          <div style="max-height: calc(4 * 88px + 40px); background-color: #fdf6ed; border-right: 1px solid #ccc; padding: 20px; text-align: center;">
            <div style="font-weight: bold; margin-bottom: 20px; font-size: 14px;">
              Technician Name
            </div>
            <div style="margin-bottom: 20px;">
              ${data.technician_name || ""}
            </div>
            <img src="${leftImage}" 
                 style="width: 100%; max-width: 150px; border: 1px solid #ccc;"
                 alt="Drill Image">
            <div style="font-weight: bold; margin-top: 20px; font-size: 14px;">
              Item Code
            </div>
            <div>
              ${data.item_code || ""}
            </div>            
          </div>
          <div style="flex: 1;">
            <table class="spare-parts-table" style="width: 100%; min-width: 600px;">
              <thead style="background-color: #f1f1f1;">
                <tr>
                                    <th>
                                        <div>.#.</div>
                                        <input type="text" class="diagram-search" placeholder="Search diagram" style="width: 100%; margin-top: 6px;" />
                                    </th>
                  <th>Image</th>
                  <th>Item name</th>
                  <th>Price</th>
                  <th>QTY</th>
                  <th>Available QTY</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
    return html;
}

function buildTableRows(items) {
    let rowsHtml = "";
    let itemCount = items ? items.length : 0;
    if (itemCount > 0) {
        items.forEach(item => {
                        const diagramNumber = item.daigram_number ?? item.custom_daigram_number ?? "";
            rowsHtml += `
                    <tr data-diagram="${diagramNumber}">
                        <td style="width: 5%;">${diagramNumber}</td>
            <td>
              <img src="${item.image || ''}" 
                   style="width: 100px; height: 70px; object-fit: cover; cursor: pointer;"
                   class="select-item"
                   data-item-code="${item.item_code}"
                                     data-daigram_number="${diagramNumber}"
                   data-item-name="${item.item_name}"
                   data-price="${item.price || 0}"
                   data-available-qty="${item.available_qty || 0}">
            </td>
            <td>${item.item_name || ''}</td>
            <td>${item.price || 0}</td>
            <td>${item.qty || 0}</td>
            <td>${item.available_qty || 0}</td>
          </tr>
        `;
        });
    }

    for (let i = itemCount; i < 4; i++) {
        rowsHtml += `
            <tr style="height: 45px;">
                <td colspan="5" style="text-align: center;">
                    ${i === 0 && itemCount === 0 ? 'No items found' : ''}
                </td>
            </tr>
        `;
    }

    return rowsHtml;
}

function addDiagramSearch(frm) {
    const wrapper = frm.get_field("spare_parts").$wrapper;
    const searchInput = wrapper.find(".diagram-search");

    searchInput.off("input").on("input", function() {
        const query = ($(this).val() || "").toString().trim().toLowerCase();
        const rows = wrapper.find("tbody tr[data-diagram]");

        rows.each(function() {
            const diagram = ($(this).attr("data-diagram") || "").toString().toLowerCase();
            const visible = !query || diagram.includes(query);
            $(this).toggle(visible);
        });
    });
}

function addClickEventsToImages(frm) {
    frm.get_field("spare_parts").$wrapper.find("img.select-item").on("click", function() {
        let item_code = $(this).data("item-code");
        let price = parseFloat($(this).data("price") || 0);

        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Item',
                name: item_code
            },
            callback: function(item_response) {
                const item_details = item_response.message;
                if (item_details) {
                    let item_found = false;
                    frm.doc.items.forEach(row => {
                        if (row.item_code === item_details.name) {
                            item_found = true;
                            let new_qty = row.qty + 1;
                            frappe.model.set_value(row.doctype, row.name, 'qty', new_qty);
                            frappe.model.set_value(row.doctype, row.name, 'subtotal', new_qty * row.price);
                        }
                    });

                    if (!item_found) {
                        let new_row = frm.add_child('items');
                        new_row.item_code = item_details.name;
                        new_row.item_name = item_details.item_name;
                        new_row.price = price;
                        new_row.qty = 1;
                        new_row.subtotal = price * 1;
                    }

                    frm.refresh_field('items');
                    frm.dirty();
                    frm.save();
                }
            }
        });
    });
}

if (window.jQuery) {
    console.log('jQuery is loaded');
} else {
    console.log('jQuery is NOT loaded');
}