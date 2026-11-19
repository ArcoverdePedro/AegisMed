// Mascara (DD) 9999-9999 / (DD) 99999-9999 para campos com data-phone-mask.
// O servidor guarda so os digitos (clear_strings), entao a mascara e apenas visual.
document.addEventListener('input', (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || !input.matches('[data-phone-mask]')) return;
    const digits = input.value.replace(/\D/g, '').slice(0, 11);
    const ddd = digits.slice(0, 2);
    if (digits.length > 10) {
        input.value = `(${ddd}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    } else if (digits.length > 6) {
        input.value = `(${ddd}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    } else if (digits.length > 2) {
        input.value = `(${ddd}) ${digits.slice(2)}`;
    } else {
        input.value = digits;
    }
});
