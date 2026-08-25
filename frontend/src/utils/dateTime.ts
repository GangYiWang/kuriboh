export function combineLocalDateAndTime(dateValue: string, timeValue: string): string {
  const localDateTime = new Date(`${dateValue}T${timeValue}`)
  if (!dateValue || !timeValue || Number.isNaN(localDateTime.getTime())) {
    throw new Error('请选择有效的开赛日期和开赛时间')
  }
  return localDateTime.toISOString()
}
