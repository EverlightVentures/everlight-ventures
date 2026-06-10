import React from 'react';
import { ViewProps } from 'react-native';
import styled from 'styled-components/native';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '@config/theme';

interface CardProps extends ViewProps {
  variant?: 'default' | 'elevated' | 'gradient' | 'outlined';
  padding?: keyof typeof theme.spacing;
  borderRadius?: keyof typeof theme.borderRadius;
  children: React.ReactNode;
}

const BaseCard = styled.View<{
  padding: keyof typeof theme.spacing;
  borderRadius: keyof typeof theme.borderRadius;
}>`
  padding: ${props => theme.spacing[props.padding]}px;
  border-radius: ${props => theme.borderRadius[props.borderRadius]}px;
`;

const DefaultCard = styled(BaseCard)`
  background-color: ${theme.colors.graphite};
`;

const ElevatedCard = styled(BaseCard)`
  background-color: ${theme.colors.graphite};
  ${theme.shadows.md};
`;

const OutlinedCard = styled(BaseCard)`
  background-color: transparent;
  border-width: 1px;
  border-color: ${theme.colors.mediumGray};
`;

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  borderRadius = 'lg',
  children,
  style,
  ...props
}) => {
  if (variant === 'gradient') {
    return (
      <LinearGradient
        colors={theme.colors.gradientAccent}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[
          {
            padding: theme.spacing[padding],
            borderRadius: theme.borderRadius[borderRadius],
          },
          style,
        ]}
        {...props}
      >
        {children}
      </LinearGradient>
    );
  }

  if (variant === 'elevated') {
    return (
      <ElevatedCard padding={padding} borderRadius={borderRadius} style={style} {...props}>
        {children}
      </ElevatedCard>
    );
  }

  if (variant === 'outlined') {
    return (
      <OutlinedCard padding={padding} borderRadius={borderRadius} style={style} {...props}>
        {children}
      </OutlinedCard>
    );
  }

  return (
    <DefaultCard padding={padding} borderRadius={borderRadius} style={style} {...props}>
      {children}
    </DefaultCard>
  );
};

export default Card;
