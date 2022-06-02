# This converts the model object to a dictionary of fields and values
get_entity_dict = lambda r: {c.name: str(getattr(r, c.name)) for c in r.__table__.columns}