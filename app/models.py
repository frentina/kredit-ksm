from django.db import models

class userLogin(models.Model):
    userid = models.IntegerField(null=False)

class userData(models.Model):
    userid = models.IntegerField(null=False)
    nama_nasabah = models.TextField(default="")
    ksm_old = models.IntegerField()
    #ksm_new = models.IntegerField()
    #cicilan_per_bulan = models.TextField(default="")
    cicilanperbulan = models.IntegerField(default=0)
    tenor_old = models.IntegerField()
    tenor_new = models.IntegerField()
    interest_old = models.IntegerField()
    interest_new = models.IntegerField()
    remaining_debt = models.IntegerField()