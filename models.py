from django.db import models
from easy_thumbnails import utils
import datetime
import pickle
from easy_thumbnails import engine, utils
from django.core.files.storage import get_storage_class, default_storage, \
    Storage

DEFAULT_THUMBNAIL_STORAGE = get_storage_class(
                                        utils.get_setting('DEFAULT_STORAGE'))()

class StorageManager(models.Manager):
    _storage_cache = {}
    
    def get_storage(self, storage):
        pickled = pickle.dumps(DEFAULT_THUMBNAIL_STORAGE)
        hash = utils.get_storage_hash(pickled)
        if hash not in self._storage_cache:
            self._storage_cache[hash] = self.get_or_create(hash=hash,
                                            defaults=dict(pickle=pickled))[0]
        return self._storage_cache[hash]
        #return 

class FileManager(models.Manager):

    def get_file(self, storage, name, create=False, update_modified=None,
                 **kwargs):
        if not isinstance(storage, Storage):
            from files import DEFAULT_THUMBNAIL_STORAGE
            storage = Storage.objects.get_storage(DEFAULT_THUMBNAIL_STORAGE)
            
        kwargs.update(dict(storage=storage, name=name))
        if create:
            if update_modified:
                defaults = kwargs.setdefault('defaults', {})
                defaults['modified'] = update_modified
            object, created = self.get_or_create(**kwargs)
        else:
            kwargs.pop('defaults', None)
            try:
                object = self.get(**kwargs)
            except self.model.DoesNotExist:
                object = None
            created = False
        if update_modified and object and not created:
            if object.modified != update_modified:
                object.modified = update_modified
                object.save()
        return object


class Storage(models.Model):
    hash = models.CharField(max_length=40, editable=False, db_index=True)
    pickle = models.TextField()

    objects = StorageManager()

    def save(self, *args, **kwargs):
        self.hash = utils.get_storage_hash(self.pickle)
        super(Storage, self).save(*args, **kwargs)

    def decode(self):
        """
        Returned the unpickled storage object, or ``None`` if an error occurs
        while unpickling.
          
        """
        try:
            return pickle.loads(self.pickle)
        except:
            pass


class File(models.Model):
    storage = models.ForeignKey(Storage)
    name = models.CharField(max_length=255, db_index=True)
    modified = models.DateTimeField(default=datetime.datetime.utcnow())

    objects = FileManager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name


class Source(File):
    pass


class Thumbnail(File):
    source = models.ForeignKey(Source, related_name='thumbnails')
