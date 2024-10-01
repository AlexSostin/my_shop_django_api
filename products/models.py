from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', blank=True, null=True)
    popularity = models.IntegerField(default=0)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    

    def __str__(self):
        return self.name

    def get_products_count(self):
        """Returns the count of products in this category."""
        return self.products.count()

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['-popularity']


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    def __str__(self):
        return f"{self.name} - ${self.price:.2f}"

    def is_in_stock(self):
        """Check if the product is available in stock."""
        return self.stock > 0

    def decrease_stock(self, quantity):
        """Decrease stock by a specified quantity."""
        if quantity > self.stock:
            raise ValueError("Not enough stock")
        self.stock -= quantity
        self.save()

    class Meta:
        ordering = ['name', '-stock', '-price']
