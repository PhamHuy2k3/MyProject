from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('MyApp', '0007_alter_invoice_options_invoice_customer_address_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='payment',
			name='stock_deducted',
			field=models.BooleanField(default=False),
		),
	]
