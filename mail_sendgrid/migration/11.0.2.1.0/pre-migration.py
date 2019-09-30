def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE public.sendgrid_substitution
        SET key = regexp_replace(key, '[{}]+', '', 'g');
        
        DELETE FROM public.sendgrid_substitution
        WHERE key SIMILAR TO '%\W+%';
    """)
