./manage.py loaddata ./fixtures/auth.json
./manage.py loaddata ./fixtures/child_products.json
./manage.py oscar_import_catalogue ./fixtures/*.csv
./manage.py oscar_import_catalogue_images ./fixtures/images.tar.gz
./manage.py oscar_populate_countries --initial-only
./manage.py loaddata ./fixtures/pages.json ./fixtures/ranges.json ./fixtures/offers.json
./manage.py loaddata ./fixtures/orders.json
./manage.py clear_index --noinput
./manage.py update_index catalogue
./manage.py thumbnail cleanup
./manage.py collectstatic --noinput