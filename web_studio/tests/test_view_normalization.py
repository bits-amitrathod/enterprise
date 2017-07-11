import textwrap
from odoo.http import _request_stack
from odoo.tests.common import TransactionCase
from odoo.addons.web_studio.controllers.main import WebStudioController


class TestViewNormalization(TransactionCase):

    def setUp(self):
        super(TestViewNormalization, self).setUp()
        _request_stack.push(self)
        self.base_view = self.env.ref('base.view_partner_form')
        self.studio_controller = WebStudioController()
        self.view = self.base_view

    def _test_view_normalization(self, original, expected):
        original = original and textwrap.dedent(original)
        self.studio_controller._set_studio_view(self.view, original)

        studio_view = self.studio_controller._get_studio_view(self.view)
        studio_view = studio_view.with_context(load_all_views=True)
        normalized = studio_view.normalize()

        self.studio_controller._set_studio_view(self.view, normalized)
        self.env[self.view.model].with_context(studio=True, load_all_views=True).fields_view_get(self.view.id, self.view.type)

        normalized = normalized and normalized.strip()
        expected = expected and textwrap.dedent(expected).strip()
        self.assertEqual(normalized, expected)

    # Flatten all xpath that target nodes added by studio itself
    def test_view_normalization_00(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title"/>
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="inside">
                <field name="credit_limit"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="debit_limit"/>
              </xpath>
              <xpath expr="//field[@name='credit_limit']" position="after">
                <field name="contact_address"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title">
                    <field name="credit_limit"/>
                    <field name="contact_address"/>
                  </group>
                  <field name="id"/>
                  <group name="studio_group_E16QG_right" string="Right Title">
                    <field name="debit_limit"/>
                  </group>
                </group>
              </xpath>
            </data>
        """)

    # Delete children of deleted nodes and reanchor siblings
    def test_view_normalization_01(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title"/>
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="inside">
                <field name="credit_limit"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="debit_limit"/>
              </xpath>
              <xpath expr="//field[@name='credit_limit']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                  <group name="studio_group_E16QG_right" string="Right Title">
                    <field name="debit_limit"/>
                  </group>
                </group>
              </xpath>
            </data>
        """)

    # When there is no more sibling, we need to reanchor on the parent
    def test_view_normalization_02(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="before">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="debit_limit"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                </group>
              </xpath>
            </data>
        """)

    # When a field is deleted, other xpath that targets it need to be reanchored.
    def test_view_normalization_03(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="before">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="debit_limit"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                </group>
              </xpath>
            </data>
        """)

    # If there is nothing left in the studio view, delete it.
    def test_view_normalization_04(self):
        expected = ''
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG']" position="inside">
                <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='id']" position="after">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG']" position="replace"/>
            </data>
        """, expected)
        studio_view = self.studio_controller._set_studio_view(self.view, expected)
        studio_view = self.studio_controller._get_studio_view(self.view)
        self.assertEqual(len(studio_view), 0)

    # An after can become a replace if the following sibling has been removed.
    def test_view_normalization_05(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='mobile']" position="replace"/>
              <xpath expr="//field[@name='contact_address']" position="after">
                <field name="contract_ids"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='mobile']" position="replace">
                <field name="contract_ids"/>
              </xpath>
            </data>
        """)

    # Multiple additions of fields should not appear if it was deleted
    def test_view_normalization_06(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace">
              </xpath>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="after">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="create_date"/>
              </xpath>
            </data>
        """)

    # Consecutive xpaths around a field that was moved away can be merged.
    def test_view_normalization_07(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="contract_ids"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
              <xpath expr="//field[@name='contract_ids']" position="after">
                  <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contract_ids"/>
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # A field that was added, then moved then deleted should not appear.
    def test_view_normalization_08(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="after">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="create_date"/>
              </xpath>
            </data>
        """)

    # Fields that were added then removed should not appear in the view at all,
    # and every other xpath that was using it should be reanchored elsewhere.
    def test_view_normalization_09(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='mobile']" position="after">
                  <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='phone']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # When two fields are added after a given field, the second one will appear
    # before the first one.
    def test_view_normalization_10(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="contact_address"/>
                <field name="id"/>
              </xpath>
            </data>
        """)

    # When we add a field after another one and replace the sibling of this one,
    # everything could be done in a single replace on the sibling node.
    def test_view_normalization_11(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="after">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
              <xpath expr="//field[@name='create_uid']" position="before">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="mobile"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="id"/>
                <field name="mobile"/>
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # When closest previous node has no name, the closest next node should be
    # used instead, provided it has a name. Also, attributes need to be handled
    # in a single xpath and alphabetically sorted.
    def test_view_normalization_12(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="zzz">PAGE 1 ZZZ</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="after">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
                <attribute name="zzz">PAGE 1 ZZZ</attribute>
              </xpath>
              <xpath expr="//page[@name='internal_notes']" position="before">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
            </data>
        """)

    # Changing an already existing attribute will generate a remove line for
    # the previous value and an addition line for the new value. The removing
    # line should not close the attributes xpath, both attributes need to be
    # redefined in a single xpath.
    def test_view_normalization_13(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="string">PAGE 1</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="after">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
                <attribute name="string">PAGE 1</attribute>
              </xpath>
              <xpath expr="//page[@name='internal_notes']" position="before">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
            </data>
        """)

    # Changes at the very end of the view can't be ignored
    def test_view_normalization_14(self):
        # There is already a chatter on res.partner.form view, which is why
        # the resulting xpath is /div instead of /sheet.
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/*[last()]" position="after">
                <div class="oe_chatter">
                  <field name="message_follower_ids" widget="mail_followers"/>
                  <field name="message_ids" widget="mail_thread"/>
                </div>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/div[1]" position="after">
                <div class="oe_chatter">
                  <field name="message_follower_ids" widget="mail_followers"/>
                  <field name="message_ids" widget="mail_thread"/>
                </div>
              </xpath>
            </data>
        """)

    # Don't break on text with newlines
    def test_view_normalization_15(self):
        # New lines in text used to create a new line in the diff, desynchronizing
        # the diff lines and the tree elements iterator
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <h1>
                    THIS
                    IS
                    A MULTILINE
                    TITLE
                </h1>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <h1>
                    THIS
                    IS
                    A MULTILINE
                    TITLE
                </h1>
              </xpath>
            </data>
        """)

    def tearDown(self):
        super(TestViewNormalization, self).tearDown()
        _request_stack.pop()
