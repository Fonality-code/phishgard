lg_compile:
	uv run pybabel compile -d app/translations/
lg_extract:
	uv run pybabel extract -F babel.cfg -o messages.pot app
lg_init:
	uv run pybabel init -i messages.pot -d app/translations/ -l fr
lg_update:
	uv run pybabel update -i messages.pot -d app/translations/
clean:
	
