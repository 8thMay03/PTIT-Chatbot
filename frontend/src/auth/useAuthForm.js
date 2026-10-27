import { useCallback, useRef, useState } from "react";
import { describeAuthError } from "./validation";

/**
 * Trạng thái chung của form đăng nhập/đăng ký: giá trị, lỗi theo trường, lỗi chung,
 * đang gửi. Lỗi client chặn gửi và đưa focus tới ô sai đầu tiên; lỗi server được
 * phân loại bằng `describeAuthError`.
 */
export function useAuthForm({ initialValues, fieldOrder, validate, submit, mode, onSuccess }) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [registrationClosed, setRegistrationClosed] = useState(false);
  const fieldRefs = useRef({});
  const submittingRef = useRef(false);

  const setField = useCallback((field, value) => {
    setValues((current) => ({ ...current, [field]: value }));
    // Sửa ô nào thì bỏ lỗi của ô đó; lỗi chung giữ tới lần gửi sau.
    setErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }, []);

  const registerRef = useCallback(
    (field) => (element) => {
      fieldRefs.current[field] = element;
    },
    []
  );

  function focusFirstError(fieldErrors) {
    const first = fieldOrder.find((field) => fieldErrors[field]);
    if (first) fieldRefs.current[first]?.focus();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;
    const clientErrors = validate(values);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length > 0) {
      setFormError(null);
      focusFirstError(clientErrors);
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setFormError(null);
    try {
      const result = await submit(values);
      onSuccess(result);
    } catch (error) {
      const described = describeAuthError(error, mode);
      setErrors(described.fields);
      setFormError(described.message);
      if (described.registrationClosed) setRegistrationClosed(true);
      focusFirstError(described.fields);
      submittingRef.current = false;
      setSubmitting(false);
    }
    // Thành công: giữ trạng thái "đang gửi" cho tới khi trang chuyển đi.
  }

  return {
    values,
    errors,
    formError,
    submitting,
    registrationClosed,
    setField,
    registerRef,
    handleSubmit,
  };
}
