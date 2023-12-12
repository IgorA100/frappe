# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import getpass

import frappe
from frappe.geo.doctype.country.country import import_country_and_currency
from frappe.utils import cint
from frappe.utils.password import update_password


def before_install():
	frappe.reload_doc("core", "doctype", "doctype_state")
	frappe.reload_doc("core", "doctype", "docfield")
	frappe.reload_doc("core", "doctype", "docperm")
	frappe.reload_doc("core", "doctype", "doctype_action")
	frappe.reload_doc("core", "doctype", "doctype_link")
	frappe.reload_doc("desk", "doctype", "form_tour_step")
	frappe.reload_doc("desk", "doctype", "form_tour")
	frappe.reload_doc("core", "doctype", "doctype")


def after_install():
	create_user_type()
	install_basic_docs()

	from frappe.core.doctype.file.utils import make_home_folder
	from frappe.core.doctype.language.language import sync_languages

	make_home_folder()
	import_country_and_currency()
	sync_languages()

	# save default print setting
	print_settings = frappe.get_doc("Print Settings")
	print_settings.save()

	# all roles to admin
	frappe.get_doc("User", "Administrator").add_roles(*frappe.get_all("Role", pluck="name"))

	# update admin password
	update_password("Administrator", get_admin_password())

	if not frappe.conf.skip_setup_wizard:
		# only set home_page if the value doesn't exist in the db
		if not frappe.db.get_default("desktop:home_page"):
			frappe.db.set_default("desktop:home_page", "setup-wizard")
			frappe.db.set_single_value("System Settings", "setup_complete", 0)

	# clear test log
	with open(frappe.get_site_path(".test_log"), "w") as f:
		f.write("")

	add_standard_navbar_items()

	frappe.db.commit()


def create_user_type():
	for user_type in ["System User", "Website User"]:
		if not frappe.db.exists("User Type", user_type):
			frappe.get_doc({"doctype": "User Type", "name": user_type, "is_standard": 1}).insert(
				ignore_permissions=True
			)


def install_basic_docs():
	# core users / roles
	install_docs = [
		{
			"doctype": "User",
			"name": "Administrator",
			"first_name": "Administrator",
			"email": "admin@example.com",
			"enabled": 1,
			"is_admin": 1,
			"roles": [{"role": "Administrator"}],
			"thread_notify": 0,
			"send_me_a_copy": 0,
		},
		{
			"doctype": "User",
			"name": "Guest",
			"first_name": "Guest",
			"email": "guest@example.com",
			"enabled": 1,
			"is_guest": 1,
			"roles": [{"role": "Guest"}],
			"thread_notify": 0,
			"send_me_a_copy": 0,
		},
		{"doctype": "Role", "role_name": "Report Manager"},
		{"doctype": "Role", "role_name": "Translator"},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Pending",
			"icon": "question-sign",
			"style": "",
		},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Approved",
			"icon": "ok-sign",
			"style": "Success",
		},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Rejected",
			"icon": "remove",
			"style": "Danger",
		},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Approve"},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Reject"},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Review"},
		{
			"doctype": "Email Domain",
			"domain_name": "example.com",
			"email_id": "account@example.com",
			"password": "pass",
			"email_server": "imap.example.com",
			"use_imap": 1,
			"smtp_server": "smtp.example.com",
		},
		{
			"doctype": "Email Account",
			"domain": "example.com",
			"email_id": "notifications@example.com",
			"default_outgoing": 1,
		},
		{
			"doctype": "Email Account",
			"domain": "example.com",
			"email_id": "replies@example.com",
			"default_incoming": 1,
		},
	]

	for d in install_docs:
		try:
			frappe.get_doc(d).insert(ignore_if_duplicate=True)
		except frappe.NameError:
			pass


def get_admin_password():
	def ask_admin_password():
		admin_password = getpass.getpass("Set Administrator password: ")
		admin_password2 = getpass.getpass("Re-enter Administrator password: ")
		if admin_password != admin_password2:
			print("\nPasswords do not match")
			return ask_admin_password()
		return admin_password

	admin_password = frappe.conf.get("admin_password")
	if not admin_password:
		return ask_admin_password()
	return admin_password


def before_tests():
	if len(frappe.get_installed_apps()) > 1:
		# don't run before tests if any other app is installed
		return

	frappe.db.truncate("Custom Field")
	frappe.db.truncate("Event")

	frappe.clear_cache()

	# complete setup if missing
	if not cint(frappe.db.get_single_value("System Settings", "setup_complete")):
		complete_setup_wizard()

	frappe.db.set_single_value("Website Settings", "disable_signup", 0)
	frappe.db.commit()
	frappe.clear_cache()


def complete_setup_wizard():
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{
			"language": "English",
			"email": "test@erpnext.com",
			"full_name": "Test User",
			"password": "test",
			"country": "United States",
			"timezone": "America/New_York",
			"currency": "USD",
			"enable_telemtry": 1,
		}
	)


def add_standard_navbar_items():
	navbar_settings = frappe.get_single("Navbar Settings")

	# don't add settings/help options if they're already present
	if navbar_settings.settings_dropdown and navbar_settings.help_dropdown:
		return

	standard_navbar_items = [
		{
			"item_label": "My Profile",
			"item_type": "Route",
			"route": "/app/user-profile",
			"is_standard": 1,
		},
		{
			"item_label": "My Settings",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.route_to_user()",
			"is_standard": 1,
		},
		{
			"item_label": "Session Defaults",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.setup_session_defaults()",
			"is_standard": 1,
		},
		{
			"item_label": "Reload",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.clear_cache()",
			"is_standard": 1,
		},
		{
			"item_label": "View Website",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.view_website()",
			"is_standard": 1,
		},
		{
			"item_label": "Toggle Full Width",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.toggle_full_width()",
			"is_standard": 1,
		},
		{
			"item_label": "Toggle Theme",
			"item_type": "Action",
			"action": "new frappe.ui.ThemeSwitcher().show()",
			"is_standard": 1,
		},
		{
			"item_type": "Separator",
			"is_standard": 1,
			"item_label": "",
		},
		{
			"item_label": "Log out",
			"item_type": "Action",
			"action": "frappe.app.logout()",
			"is_standard": 1,
		},
	]

	standard_help_items = [
		{
			"item_label": "About",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.show_about()",
			"is_standard": 1,
		},
		{
			"item_label": "Keyboard Shortcuts",
			"item_type": "Action",
			"action": "frappe.ui.toolbar.show_shortcuts(event)",
			"is_standard": 1,
		},
		{
			"item_label": "Frappe Support",
			"item_type": "Route",
			"route": "https://frappe.io/support",
			"is_standard": 1,
		},
	]

	navbar_settings.settings_dropdown = []
	navbar_settings.help_dropdown = []

	for item in standard_navbar_items:
		navbar_settings.append("settings_dropdown", item)

	for item in standard_help_items:
		navbar_settings.append("help_dropdown", item)

	navbar_settings.save()
