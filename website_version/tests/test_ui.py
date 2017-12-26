import odoo.tests


@odoo.tests.tagged('post_install','-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_versioning(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('versioning')", "odoo.__DEBUG__.services['web_tour.tour'].tours.versioning.ready", login='admin')
