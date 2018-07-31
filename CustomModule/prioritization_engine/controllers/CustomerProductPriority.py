

class CustomerProductPriority:

    def __init__(self, customer, product_id, product_priority, auto_allocate, cooling_period, last_purchased_date, length_of_hold, partial_order, expiration_tolerance, product_quantity):
        self.customer = customer
        self.product_id = product_id
        self.product_priority = product_priority
        self.auto_allocate = auto_allocate
        self.cooling_period = cooling_period
        self.last_purchased_date = last_purchased_date
        self.length_of_hold = length_of_hold
        self.partial_order = partial_order
        self.expiration_tolerance = expiration_tolerance
        self.product_quantity = product_quantity


