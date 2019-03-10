from django import forms

class PatchForm(forms.Form):
    patch = forms.CharField(max_length=255)