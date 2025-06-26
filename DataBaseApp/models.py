from django.db import models

class Brand(models.Model):
    name = models.CharField(max_length=255)

class Device(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    codename = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=100)
    platform = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    url = models.URLField()
    flash = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=255)
    
    display_width_px  = models.PositiveIntegerField(blank=True, null=True)
    display_height_px = models.PositiveIntegerField(blank=True, null=True)
    
    cameras = models.ManyToManyField(
        'Camera',
        through='DeviceCamera',
        related_name='devices'
    )
    @property
    def display_ratio(self):
        if self.display_width_px and self.display_height_px:
            return self.display_height_px / self.display_width_px
        return None

class Sensor(models.Model):
    sensor_type   = models.CharField(max_length=100)
    sensor_format = models.CharField(max_length=100, blank=True, null=True)
    pixel_size    = models.CharField(max_length=50,  blank=True, null=True)

    class Meta:
       
        unique_together = ('sensor_type', 'sensor_format', 'pixel_size')

class Camera(models.Model):
    sensor        = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True)
    type          = models.CharField(max_length=100)
    resolution    = models.CharField(max_length=50, blank=True, null=True)
    num_pixels    = models.CharField(max_length=50, blank=True, null=True)
    aperture      = models.CharField(max_length=20, blank=True, null=True)
    MEFL          = models.CharField(max_length=20, blank=True, null=True)
    focus         = models.CharField(max_length=255, blank=True, null=True)
    zoom          = models.CharField(max_length=20, blank=True, null=True)
    placement     = models.CharField(max_length=50, blank=True, null=True)
    features      = models.ManyToManyField('Feature', through='Camera_Features')
    media_formats = models.ManyToManyField('Media_Format', through='Camera_Medias')

class DeviceCamera(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('device', 'camera')

class Feature(models.Model):
    name = models.CharField(max_length=255)

class Media_Format(models.Model):
    format_type      = models.CharField(max_length=50)
    format_extension = models.CharField(max_length=20)

class Camera_Features(models.Model):
    camera  = models.ForeignKey(Camera, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)

class Camera_Medias(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    format = models.ForeignKey(Media_Format, on_delete=models.CASCADE)
