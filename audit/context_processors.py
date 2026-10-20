def institution_context(request):
    """
    Menyediakan pengaturan instansi global ke template (nama instansi, logo, dsb.)
    """
    try:
        from audit.models import InstitutionSetting
        setting = InstitutionSetting.objects.first()
    except Exception:
        setting = None

    return {
        'institution_setting': setting,
        'app_name': 'SIP3B - Sistem Informasi Peminjaman & Penyerahan Barang'
    }
