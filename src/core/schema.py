from datetime import date

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class BirthdaysSchema(Schema):
    """Schema for birthdays

    Extends `Schema` from `marshmallow`. Used for validating the data of the birthdays.
    Matches schema of the API.

    Attributes:
        name (fields.String): name of the birthday person
        day (fields.Integer): day of the birthday
        month (fields.Integer): month of the birthday
        year (fields.Integer): year of the birthday, optional
        note (fields.String): note for the birthday, optional
    """

    name = fields.String(required=True, validate=validate.Length(max=255))
    day = fields.Integer(required=True)
    month = fields.Integer(required=True)
    year = fields.Integer(allow_none=True)
    note = fields.String(allow_none=True, validate=validate.Length(max=255))

    @validates_schema
    def valid_date(self, data, **kwargs):
        """Validates the date

        Checks if the date is valid and if it's not in the future.

        Args:
            data (dict): data to be validated. Has to contain keys: `day`, `month`.
              `year` is optional.
            **kwargs: additional arguments

        Raises:
            ValidationError: if the date is invalid, in the future or 29th of February.
        """

        try:
            year = data["year"]
            if year is None:
                raise KeyError
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
