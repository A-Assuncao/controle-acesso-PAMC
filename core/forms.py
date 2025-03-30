from django import forms
from django.utils import timezone
from .models import Servidor, RegistroAcesso

class ServidorForm(forms.ModelForm):
    class Meta:
        model = Servidor
        fields = ['nome', 'numero_documento', 'veiculo', 'setor']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'veiculo': forms.TextInput(attrs={'class': 'form-control'}),
            'setor': forms.TextInput(attrs={'class': 'form-control'})
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo_funcionario = cleaned_data.get('tipo_funcionario')
        plantao = cleaned_data.get('plantao')
        
        if tipo_funcionario == 'PLANTONISTA' and not plantao:
            raise forms.ValidationError('Para plantonistas, o plantão é obrigatório.')
            
        if tipo_funcionario != 'PLANTONISTA' and plantao:
            raise forms.ValidationError('O plantão só deve ser informado para plantonistas.')
            
        return cleaned_data

class RegistroAcessoForm(forms.ModelForm):
    data_hora_manual = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        )
    )
    
    class Meta:
        model = RegistroAcesso
        fields = ['servidor', 'tipo_acesso', 'observacao', 'isv']
        widgets = {
            'servidor': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acesso': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'isv': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_hora_manual = cleaned_data.get('data_hora_manual')
        justificativa = cleaned_data.get('justificativa')
        
        if data_hora_manual:
            if not justificativa or len(justificativa) < 200:
                raise forms.ValidationError(
                    'Para registros manuais, é necessário fornecer uma justificativa com pelo menos 200 caracteres.'
                )
            
            if data_hora_manual > timezone.now():
                raise forms.ValidationError(
                    'A data/hora manual não pode ser no futuro.'
                )
        
        return cleaned_data 