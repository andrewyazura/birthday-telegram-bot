from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import date


class BirthdaysSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(max=255))
    day = fields.Integer(required=True)
    month = fields.Integer(required=True)
    year = fields.Integer()
    note = fields.String()

    @validates_schema
    def valid_date(self, data, **kwargs):
        try:
            year = data["year"]
        except KeyError:
            year = date.today().year - 1

        if (data["month"] == 2) and (data["day"] == 29):
            raise ValidationError(
                "29th of February is forbidden. Choose 28.02 or 1.03:"
            )

        try:
            birthday = date(year, data["month"], data["day"])
        except ValueError:
            raise ValidationError("Invalid date, try again:")
        if date.today() < birthday:
            raise ValidationError("Future dates are forbidden, try again:")
