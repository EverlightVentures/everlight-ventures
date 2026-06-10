import React from 'react';
import { Text as RNText, TextProps as RNTextProps, TextStyle } from 'react-native';
import { theme, typography } from '@config/theme';

type TypographyVariant = keyof typeof typography;

interface CustomTextProps extends RNTextProps {
  variant?: TypographyVariant;
  color?: string;
  align?: 'left' | 'center' | 'right' | 'justify';
}

export const Text: React.FC<CustomTextProps> = ({
  variant = 'body',
  color,
  align = 'left',
  style,
  children,
  ...props
}) => {
  const variantStyle = typography[variant];

  const textStyle: TextStyle = {
    ...variantStyle,
    ...(color && { color }),
    textAlign: align,
  };

  return (
    <RNText style={[textStyle, style]} {...props}>
      {children}
    </RNText>
  );
};

export default Text;
