odoo.define('web_studio.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var utils = require('web_studio.utils');

var _t = core._t;

tour.register('web_studio_home_menu_background_tour', {
    url: "/web",
}, [{
    trigger: '.o_web_studio_navbar_item',
    content: _t('Want to customize the background? Let’s activate <b>Odoo Studio</b>.'),
    position: 'bottom',
    extra_trigger: '.o_home_menu',
}, {
    trigger: '.o_web_studio_home_studio_menu a',
    content: _t('Click here.'),
    position: 'right',
}, {
    trigger: '.o_web_studio_home_studio_menu ul.dropdown-menu li:eq(0)',
    content: _t('Change the <b>background</b>, make it yours.'),
    position: 'bottom',
}]);

tour.register('web_studio_new_app_tour', {
    url: "/web?studio=app_creator",
}, [{
    trigger: '.o_web_studio_new_app',
    auto: true,
    position: 'bottom',
},{
    trigger: '.o_web_studio_app_creator_next',
    content: _t('I bet you can <b>build an app</b> in 5 minutes. Ready for the challenge?'),
    position: 'top',
}, {
    trigger: '.o_web_studio_app_creator_name > input',
    content: _t('How do you want to <b>name</b> your app? Library, Academy, …?'),
    position: 'right',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_selectors .o_web_studio_selector:eq(2)',
    content: _t('Now, customize your icon. Make it yours.'),
    position: 'top',
}, {
    trigger: '.o_web_studio_app_creator_next.is_ready',
    content: _t('Go on, you are almost done!'),
    position: 'top',
}, {
    trigger: '.o_web_studio_app_creator_menu > input',
    content: _t('How do you want to name your first <b>menu</b>? My books, My courses?'),
    position: 'right',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_app_creator_next.is_ready',
    content: _t('You are just one click away from <b>generating your first app</b>.'),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char',
    content: _t('Nicely done! Let’s build your screen now; <b>drag</b> a <i>text field</i> and <b>drop</b> it in your view, on the right.'),
    position: 'bottom',
    run: 'drag_and_drop .o_web_studio_form_view_editor .o_group',
}, {
    trigger: '.o_web_studio_form_view_editor td.o_td_label',
    content: _t('To <b>customize a field</b>, click on its <i>label</i>.'),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_sidebar_content.o_display_field input[name="string"]',
    content: _t('Here, you can <b>name</b> your field (e.g. Book reference, ISBN, Internal Note, etc.).'),
    position: 'bottom',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_sidebar .o_web_studio_new',
    content: _t('Good job! To add more <b>fields</b>, come back to the <i>Add tab</i>.'),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_selection',
    content: _t('Drag & drop <b>another field</b>. Let’s try with a <i>selection field</i>.'),
    position: 'bottom',
    run: 'drag_and_drop .o_web_studio_form_view_editor .o_group',
}, {
    trigger: '.o_web_studio_field_dialog_form > .o_web_studio_selection_new_value > input',
    content: _t("Create your <b>selection values</b> (e.g.: Romance, Polar, Fantasy, etc.)"),
    position: 'top',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_field_dialog_form > .o_web_studio_selection_new_value button',
    auto: true,
}, {
    trigger: '.modal-footer > button:eq(0)',
    auto: true,
}, {
    trigger: '.o_web_studio_add_chatter',
    content: _t("Add a <b>chatter widget</b> to allow discussions on your document: by email or inline."),
    position: 'top',
}, {
    trigger: '.o_web_studio_form_view_editor .oe_chatter',
    content: _t("Click to edit."),
    position: 'top',
}, {
    trigger: '.o_web_studio_sidebar .o_display_chatter input[name="email_alias"]',
    content: _t("Set an <b>email alias</b>. Then, try to send an email to this address; it will create a document automatically for you. Pretty cool, huh?"),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_leave',
    content: _t("Let’s check the result. Close Odoo Studio to get an <b>overview of your app</b>."),
    position: 'left',
}, {
    trigger: 'input.o_required_modifier',
    auto: true,
    position: 'bottom',
}, {
    trigger: '.o_control_panel .o_cp_buttons .o_form_button_save',
    content: _t("Save."),
    position: 'right',
},  {
    trigger: '.o_web_studio_navbar_item',
    extra_trigger: '.o_form_view.o_form_readonly',
    content: _t("Wow, nice! And I’m sure you can make it even better! Use this icon to open <b>Odoo Studio</b> and customize any screen."),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_menu .o_menu_sections a[data-name="views"]',
    content: _t("Want more fun? Let’s create more <b>views</b>."),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="kanban"] .o_web_studio_thumbnail',
    content: _t("What about a <b>Kanban view</b>?"),
    position: 'bottom',
}, {
    trigger: '.o_web_studio_sidebar .o_web_studio_new',
    content: _t("Now you’re on your own. Enjoy your <b>super power</b>."),
    position: 'bottom',
}]);

tour.register('web_studio_tests_tour', {
    test: true,
    url: "/web?studio=app_creator&debug=",
}, [{
    trigger: '.o_web_studio_new_app',
},{
    // the next 6 steps are here to create a new app
    trigger: '.o_web_studio_app_creator_next',
}, {
    trigger: '.o_web_studio_app_creator_name > input',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_selectors .o_web_studio_selector:eq(2)',
}, {
    trigger: '.o_web_studio_app_creator_next.is_ready',
}, {
    trigger: '.o_web_studio_app_creator_menu > input',
    run: 'text ' + utils.randomString(6),
}, {
    trigger: '.o_web_studio_app_creator_next.is_ready',
}, {
    // add an existing field (display_name)
    trigger: '.o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char',
    run: 'drag_and_drop .o_web_studio_form_view_editor .o_group',
}, {
    // click on the field
    trigger: '.o_web_studio_form_view_editor td.o_td_label:first',
}, {
    // rename the label
    trigger: '.o_web_studio_sidebar_content.o_display_field input[name="string"]',
    run: 'text My Coucou Field',
}, {
    // verify that the field name has changed and change it
    trigger: 'input[data-type="field_name"][value="my_coucou_field"]',
    run: 'text coucou',
}, {
    // click on "Add" tab
    trigger: '.o_web_studio_sidebar .o_web_studio_new',
}, {
    // add a new field
    trigger: '.o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char',
    run: 'drag_and_drop .o_web_studio_form_view_editor .o_group',
}, {
    // click on the new field
    trigger: '.o_web_studio_form_view_editor td.o_td_label:eq(1)',
}, {
    // rename the field with the same name
    trigger: 'input[data-type="field_name"]',
    run: 'text coucou',
}, {
    // an alert dialog should be opened
    trigger: '.modal-footer > button:first',
}, {
    // rename the label
    trigger: '.o_web_studio_sidebar_content.o_display_field input[name="string"]',
    run: 'text COUCOU',
}, {
    // verify that the field name has changed (post-fixed by _1)
    trigger: 'input[data-type="field_name"][value="coucou_1"]',
    run: 'text coucou_2',
}, {
    // add a statusbar
    trigger: '.o_web_studio_statusbar_hook',
}, {
    trigger: '.modal-footer .btn.btn-primary',
}, {
    trigger: '.o_statusbar_status',
}, {
    // verify that a default value has been set for the statusbar
    trigger: '.o_web_studio_sidebar select[name="default_value"]:contains(First Status)',
}, {
    // switch in list view
    trigger: '.o_web_studio_menu .o_web_studio_views_icons a[data-name="list"]',
}, {
    // add an existing field (display_name)
    trigger: '.o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char',
    run: 'drag_and_drop .o_web_studio_list_view_editor th.o_web_studio_hook:first',
}, {
    trigger: '.o_web_studio_list_view_editor th:contains("COUCOU")',
}, {
    trigger: '.o_web_studio_leave',
}, {
    // re-open studio
    trigger: '.o_web_studio_navbar_item',
}, {
    // edit action
    trigger: '.o_web_studio_menu .o_menu_sections a[data-name="views"]',
}, {
    // add a kanban
    trigger: '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="kanban"] .o_web_studio_thumbnail',
}, {
    // enable stages
    trigger: '.o_web_studio_sidebar input[name=enable_stage]',
}, {
    // toggle the home menu
    trigger: '.o_menu_toggle',
}, {
    // a invisible element cannot be used as a trigger so this small hack is
    // mandatory for the next step
    trigger: '.o_app[data-menu-xmlid*="studio"]:first',
    run: function () {
        this.$anchor.find('.o_web_studio_edit_icon').css('visibility', 'visible');
    },
}, {
    // edit an app
    trigger: '.o_app[data-menu-xmlid*="studio"]:first .o_web_studio_edit_icon',
}, {
    // design the icon
    trigger: '.o_web_studio_selector[data-type="background_color"]',
}, {
    trigger: '.o_web_studio_palette > .o_web_studio_selector:first',
}, {
    trigger: '.modal-footer .btn.btn-primary',
}]);

});
