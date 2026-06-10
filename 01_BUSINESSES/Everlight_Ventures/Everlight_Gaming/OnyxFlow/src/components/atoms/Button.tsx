import React from 'react';
import {
  TouchableOpacity,
  TouchableOpacityProps,
  ViewStyle,
  ActivityIndicator,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import styled from 'styled-components/native';
import { theme } from '@config/theme';
import Text from './Text';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'gold';
type ButtonSize = 'small' | 'medium' | 'large';

interface ButtonProps extends TouchableOpacityProps {
  title: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
}

const ButtonContainer = styled(TouchableOpacity)<{
  fullWidth?: boolean;
  size: ButtonSize;
}>`
  ${props => props.fullWidth && 'width: 100%;'}
  align-items: center;
  justify-content: center;
  flex-direction: row;
  border-radius: ${props => {
    if (props.size === 'small') return theme.borderRadius.md;
    if (props.size === 'large') return theme.borderRadius.xl;
    return theme.borderRadius.lg;
  }}px;
  ${props => {
    if (props.size === 'small')
      return `padding: ${theme.spacing.sm}px ${theme.spacing.md}px;`;
    if (props.size === 'large')
      return `padding: ${theme.spacing.lg}px ${theme.spacing.xl}px;`;
    return `padding: ${theme.spacing.md}px ${theme.spacing.lg}px;`;
  }}
`;

const OutlineButton = styled(ButtonContainer)<{ variant: ButtonVariant }>`
  background-color: transparent;
  border-width: 2px;
  border-color: ${props =>
    props.variant === 'gold' ? theme.colors.champagneGold : theme.colors.white};
`;

const GhostButton = styled(ButtonContainer)`
  background-color: transparent;
`;

const SolidButton = styled(ButtonContainer)<{ variant: ButtonVariant }>`
  background-color: ${props => {
    if (props.variant === 'secondary') return theme.colors.graphite;
    if (props.variant === 'gold') return theme.colors.champagneGold;
    return theme.colors.white;
  }};
`;

export const Button: React.FC<ButtonProps> = ({
  title,
  variant = 'primary',
  size = 'medium',
  loading = false,
  fullWidth = false,
  icon,
  disabled,
  ...props
}) => {
  const textVariant = size === 'small' ? 'buttonSmall' : 'button';

  const textColor =
    variant === 'outline' || variant === 'ghost'
      ? variant === 'gold'
        ? theme.colors.champagneGold
        : theme.colors.white
      : variant === 'gold'
        ? theme.colors.onyxBlack
        : theme.colors.onyxBlack;

  if (variant === 'outline') {
    return (
      <OutlineButton
        variant={variant}
        size={size}
        fullWidth={fullWidth}
        disabled={disabled || loading}
        activeOpacity={0.7}
        {...props}
      >
        {loading ? (
          <ActivityIndicator
            color={variant === 'gold' ? theme.colors.champagneGold : theme.colors.white}
          />
        ) : (
          <>
            {icon && <>{icon}</>}
            <Text variant={textVariant} color={textColor}>
              {title}
            </Text>
          </>
        )}
      </OutlineButton>
    );
  }

  if (variant === 'ghost') {
    return (
      <GhostButton
        size={size}
        fullWidth={fullWidth}
        disabled={disabled || loading}
        activeOpacity={0.7}
        {...props}
      >
        {loading ? (
          <ActivityIndicator color={theme.colors.white} />
        ) : (
          <>
            {icon && <>{icon}</>}
            <Text variant={textVariant} color={textColor}>
              {title}
            </Text>
          </>
        )}
      </GhostButton>
    );
  }

  // For primary variant, use gradient
  if (variant === 'primary') {
    return (
      <TouchableOpacity
        disabled={disabled || loading}
        activeOpacity={0.7}
        style={{ width: fullWidth ? '100%' : 'auto' }}
        {...props}
      >
        <LinearGradient
          colors={theme.colors.gradientBlackToGraphite}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={{
            borderRadius:
              size === 'small'
                ? theme.borderRadius.md
                : size === 'large'
                  ? theme.borderRadius.xl
                  : theme.borderRadius.lg,
            paddingVertical: size === 'small' ? theme.spacing.sm : size === 'large' ? theme.spacing.lg : theme.spacing.md,
            paddingHorizontal: size === 'small' ? theme.spacing.md : size === 'large' ? theme.spacing.xl : theme.spacing.lg,
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'row',
          }}
        >
          {loading ? (
            <ActivityIndicator color={theme.colors.white} />
          ) : (
            <>
              {icon && <>{icon}</>}
              <Text variant={textVariant} color={theme.colors.white}>
                {title}
              </Text>
            </>
          )}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  // Solid buttons (secondary, gold)
  return (
    <SolidButton
      variant={variant}
      size={size}
      fullWidth={fullWidth}
      disabled={disabled || loading}
      activeOpacity={0.7}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <>
          {icon && <>{icon}</>}
          <Text variant={textVariant} color={textColor}>
            {title}
          </Text>
        </>
      )}
    </SolidButton>
  );
};

export default Button;
